import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import io

from core.business_rules import (
    get_default_policy_tiers,
    get_allowed_term,
    generate_installments,
    calculate_terms,
    Installment,
    PolicyTier,
)

# Configuracao da Pagina
st.set_page_config(
    page_title="Calculador de Prazo Medio",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilizacao CSS Corporativa e Dark Mode Refinado
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Cards de Indicadores */
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        min-height: 110px;
    }
    
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        margin-bottom: 0.25rem;
    }
    
    .metric-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #F8FAFC;
    }

    .metric-sub {
        font-size: 0.775rem;
        color: #64748B;
        margin-top: 0.35rem;
    }

    /* Badges de Parecer Comercial */
    .badge-approved {
        background-color: #064E3B;
        color: #A7F3D0;
        border: 1px solid #059669;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }

    .badge-rejected {
        background-color: #450A0A;
        color: #FECACA;
        border: 1px solid #DC2626;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }

    .badge-divergent {
        background-color: #78350F;
        color: #FDE68A;
        border: 1px solid #D97706;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }

    /* Banners Informativos e de Erro */
    .banner-danger {
        background-color: #1E293B;
        border-left: 4px solid #EF4444;
        border-radius: 0 6px 6px 0;
        padding: 0.85rem 1.15rem;
        margin-top: 0.75rem;
        margin-bottom: 1.25rem;
        color: #FCA5A5;
        font-size: 0.9rem;
    }

    .banner-warning {
        background-color: #1E293B;
        border-left: 4px solid #F59E0B;
        border-radius: 0 6px 6px 0;
        padding: 0.85rem 1.15rem;
        margin-top: 0.75rem;
        margin-bottom: 1.25rem;
        color: #FCD34D;
        font-size: 0.9rem;
    }

    .banner-success {
        background-color: #1E293B;
        border-left: 4px solid #10B981;
        border-radius: 0 6px 6px 0;
        padding: 0.85rem 1.15rem;
        margin-top: 0.75rem;
        margin-bottom: 1.25rem;
        color: #6EE7B7;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def parse_br_currency(val_input: str, default: float = 0.0) -> float:
    """Converte string de moeda brasileira (ex: '119.000,00' ou '119000') para float."""
    if not val_input:
        return default
    s = str(val_input).replace("R$", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        if s.count(".") > 1:
            s = s.replace(".", "")
        elif s.count(".") == 1:
            parts = s.split(".")
            if len(parts[1]) == 3 and float(parts[0]) >= 1:
                s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return default


def format_currency_br(val: float) -> str:
    """Formata numero float para formato com pontuacao brasileira R$ 119.000,00."""
    try:
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def format_number_br(val: float) -> str:
    """Formata numero float para formato pontuado sem cifrao 119.000,00."""
    try:
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


# Inicializacao de estado da sessao
if "policy_tiers" not in st.session_state:
    st.session_state.policy_tiers = get_default_policy_tiers()

if "total_val_str" not in st.session_state:
    st.session_state.total_val_str = "119.000,00"

if "down_payment_str" not in st.session_state:
    st.session_state.down_payment_str = "40.000,00"

if "reset_trigger" not in st.session_state:
    st.session_state.reset_trigger = 0


# ==============================================================================
# BARRA LATERAL: PARAMETROS DA NEGOCIACAO (SEM REDUNDANCIA)
# ==============================================================================
with st.sidebar:
    st.markdown("### Parametros da Negociacao")
    st.caption("Configuracoes financeiras da proposta.")
    
    st.markdown("---")
    
    closing_date = st.date_input(
        "Data de Fechamento",
        value=date.today(),
        help="Data de partida (dia zero) para apuracao dos prazos corridos.",
        format="DD/MM/YYYY",
    )
    
    # Campo de valor total formatado diretamente com pontuacao de milhares
    total_input = st.text_input(
        "Valor Total do Orcamento (R$)",
        value=st.session_state.total_val_str,
        help="Informe o valor negociado. Exemplo: 119.000,00",
    )
    total_val = parse_br_currency(total_input, default=119000.0)
    # Mantem a string formatada consistente
    st.session_state.total_val_str = format_number_br(total_val)
    
    # Campo de entrada formatado diretamente com pontuacao de milhares
    down_input = st.text_input(
        "Valor da Entrada (R$)",
        value=st.session_state.down_payment_str,
        help="Montante pago na primeira parcela. Exemplo: 40.000,00",
    )
    down_payment = parse_br_currency(down_input, default=40000.0)
    down_payment = min(down_payment, total_val)
    st.session_state.down_payment_str = format_number_br(down_payment)
    
    num_installments = st.number_input(
        "Numero de Parcelas",
        min_value=1,
        max_value=24,
        value=5,
        step=1,
        help="Quantidade total de parcelas (incluindo a entrada).",
    )
    
    st.markdown("---")
    st.markdown("##### Regras de Vencimento Inicial")
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        first_due_days = st.number_input("1º Venc. (dias)", min_value=0, max_value=180, value=10)
    with col_sb2:
        interval_days = st.number_input("Intervalo (dias)", min_value=1, max_value=180, value=31)

    if st.button("Restaurar Rateio Padrao", use_container_width=True):
        st.session_state.reset_trigger += 1
        st.rerun()


# ==============================================================================
# CORPO PRINCIPAL
# ==============================================================================

st.markdown("### Analise de Prazo Medio e Politica Comercial")
st.caption("Validacao de condicoes de pagamento conforme limites de credito da empresa.")

# 1. Geracao base de parcelas conforme parametros da barra lateral
base_installments = generate_installments(
    closing_date=closing_date,
    total_value=total_val,
    down_payment=down_payment,
    num_installments=num_installments,
    first_due_days=first_due_days,
    interval_days=interval_days,
)

# 2. DataFrame para o editor interativo
df_source = pd.DataFrame([
    {
        "Parcela": f"{inst.number}ª",
        "Vencimento": inst.due_date,
        "Valor": round(float(inst.value), 2),
    }
    for inst in base_installments
])

st.markdown("##### Grade de Parcelas")
st.caption("Voce pode editar datas de vencimento ou valores diretamente na tabela:")

editor_key = f"grid_{st.session_state.reset_trigger}_{num_installments}_{total_val}_{down_payment}_{closing_date}_{first_due_days}_{interval_days}"

edited_df = st.data_editor(
    df_source,
    column_config={
        "Parcela": st.column_config.TextColumn("Parcela", disabled=True, width="small"),
        "Vencimento": st.column_config.DateColumn(
            "Data de Vencimento",
            format="DD/MM/YYYY",
            required=True,
            width="medium",
        ),
        "Valor": st.column_config.NumberColumn(
            "Valor da Parcela (R$)",
            format="R$ %.2f",
            required=True,
            step=50.0,
            width="medium",
        ),
    },
    hide_index=True,
    use_container_width=True,
    key=editor_key,
)

# 3. Reconstrucao das parcelas com base na edicao manual
custom_dates = []
custom_values = []
for _, row in edited_df.iterrows():
    raw_date = row["Vencimento"]
    if isinstance(raw_date, str):
        c_date = date.fromisoformat(raw_date)
    elif hasattr(raw_date, "date"):
        c_date = raw_date.date()
    else:
        c_date = raw_date
    custom_dates.append(c_date)
    custom_values.append(float(row["Valor"]))

current_installments = generate_installments(
    closing_date=closing_date,
    total_value=total_val,
    down_payment=down_payment,
    num_installments=num_installments,
    custom_dates=custom_dates,
    custom_values=custom_values,
)

# 4. Verificacao de Erro: Soma das parcelas vs Total Negociado
total_grid = sum(inst.value for inst in current_installments)
diff_total = round(total_grid - total_val, 2)
has_value_mismatch = abs(diff_total) > 0.05

# 5. Calculo das metricas financeiras
result = calculate_terms(
    closing_date=closing_date,
    total_value=total_val,
    down_payment=down_payment,
    installments=current_installments,
    policy_tiers=st.session_state.policy_tiers,
)

# ==============================================================================
# ALERTA DE DIVERGENCIA OU CONFORMIDADE
# ==============================================================================
if has_value_mismatch:
    if diff_total > 0:
        st.markdown(
            f"""
            <div class="banner-danger">
                <b>Erro de Validacao:</b> A soma das parcelas ({format_currency_br(total_grid)}) 
                <b>excede</b> o valor total negociado ({format_currency_br(total_val)}) em <b>{format_currency_br(diff_total)}</b>. 
                Ajuste os valores para obter o parecer comercial.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="banner-danger">
                <b>Erro de Validacao:</b> A soma das parcelas ({format_currency_br(total_grid)}) 
                esta <b>abaixo</b> do valor total negociado ({format_currency_br(total_val)}). 
                Faltam <b>{format_currency_br(abs(diff_total))}</b> a alocar nas parcelas.
            </div>
            """,
            unsafe_allow_html=True
        )
elif not result.is_approved:
    if result.suggested_min_down_payment is not None and result.suggested_min_down_payment <= total_val:
        adicional = result.suggested_min_down_payment - down_payment
        st.markdown(
            f"""
            <div class="banner-warning">
                <b>Prazo Nao Conforme:</b> O prazo medio proporcional calculado ({result.weighted_average_term_days:.2f} dias) 
                ultrapassa o limite permitido de {result.allowed_term_days} dias.<br>
                <b>Recomendacao:</b> Para aprovar com essas mesmas datas, a entrada minima sugerida e de 
                <b>{format_currency_br(result.suggested_min_down_payment)}</b> 
                (acrescimo de <b>{format_currency_br(adicional)}</b> em relacao ao valor atual).
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="banner-warning">
                <b>Prazo Nao Conforme:</b> O prazo medio proporcional ({result.weighted_average_term_days:.2f} dias) 
                excede o limite de {result.allowed_term_days} dias. Antecipe as parcelas finais ou aumente o valor de entrada.
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.markdown(
        f"""
        <div class="banner-success">
            <b>Condicao Aprovada:</b> O prazo medio proporcional de <b>{result.weighted_average_term_days:.2f} dias</b> 
            atende a politica comercial de ate <b>{result.allowed_term_days} dias</b> para orcamentos de {format_currency_br(total_val)}.
        </div>
        """,
        unsafe_allow_html=True
    )


# ==============================================================================
# INDICADORES PRINCIPAIS (KPIs)
# ==============================================================================
st.markdown("##### Indicadores Consolidados")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Prazo Medio Ponderado</div>
            <div class="metric-value">{result.weighted_average_term_days:.2f} <span style="font-size:0.95rem;color:#94A3B8;">dias</span></div>
            <div class="metric-sub">Ponderacao financeira proporcional</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Prazo Maximo Permitido</div>
            <div class="metric-value">{result.allowed_term_days} <span style="font-size:0.95rem;color:#94A3B8;">dias</span></div>
            <div class="metric-sub">Politica para {format_currency_br(total_val)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:
    if has_value_mismatch:
        status_badge = '<div class="badge-divergent">VALOR DIVERGENTE</div>'
        status_sub = f"Diferenca de {format_currency_br(abs(diff_total))}"
    elif result.is_approved:
        status_badge = '<div class="badge-approved">CONDICAO APROVADA</div>'
        status_sub = f"Margem de {abs(result.difference_days):.2f} dias abaixo do teto"
    else:
        status_badge = '<div class="badge-rejected">PRAZO NAO PERMITIDO</div>'
        status_sub = f"Excedeu o teto em {result.difference_days:.2f} dias"

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Parecer Comercial</div>
            <div style="margin-top:0.3rem;">{status_badge}</div>
            <div class="metric-sub">{status_sub}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Data Media Ponderada</div>
            <div class="metric-value" style="font-size:1.35rem;padding-top:0.25rem;">
                {result.weighted_average_date.strftime('%d/%m/%Y')}
            </div>
            <div class="metric-sub">Prazo simples: {result.simple_average_term_days:.1f} dias</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==============================================================================
# SECOES EXPANSIVEIS (DISTRIBUICAO LIMPA E DESPOLUIDA)
# ==============================================================================

# Expander 1: Demonstrativo de Calculo dos Pesos
with st.expander("Demonstrativo Detalhado de Calculo (Pesos e Ponderacao)"):
    det_rows = []
    for inst in result.installments:
        det_rows.append({
            "Parcela": f"{inst.number}ª",
            "Vencimento": inst.due_date.strftime("%d/%m/%Y"),
            "Dias Corridos": f"{inst.days} dias",
            "Valor da Parcela": format_currency_br(inst.value),
            "Peso no Total (%)": f"{inst.factor * 100:.2f}%",
            "Contribuicao Ponderada": f"{inst.weighted_days:.2f} dias",
        })
    df_det = pd.DataFrame(det_rows)
    st.dataframe(df_det, use_container_width=True, hide_index=True)
    st.caption("A soma das contribuicoes ponderadas resulta exatamente no Prazo Medio Ponderado.")

# Expander 2: Grafico de Distribuicao e Fluxo Financeiro
with st.expander("Grafico de Distribuicao e Fluxo Financeiro"):
    fig = go.Figure()
    bar_colors = ["#2563EB" if i == 0 and down_payment > 0 else "#0284C7" for i in range(len(result.installments))]
    
    fig.add_trace(go.Bar(
        x=[inst.due_date.strftime("%d/%m/%Y") for inst in result.installments],
        y=[inst.value for inst in result.installments],
        text=[f"{format_currency_br(inst.value)}<br>({inst.factor*100:.1f}%)" for inst in result.installments],
        textposition="outside",
        marker_color=bar_colors,
        name="Valor da Parcela",
        hovertemplate="<b>%{x}</b><br>Valor: R$ %{y:,.2f}<extra></extra>",
    ))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1E293B",
        plot_bgcolor="#1E293B",
        height=320,
        margin=dict(l=20, r=20, t=30, b=30),
        yaxis=dict(showgrid=True, gridcolor="#334155", title="Valor da Parcela (R$)"),
        xaxis=dict(showgrid=False, title="Vencimento"),
    )
    st.plotly_chart(fig, use_container_width=True)

# Expander 3: Politica Comercial Vigente
with st.expander("Politica Comercial (Tabela de Faixas e Prazos)"):
    tiers_data = []
    for t in st.session_state.policy_tiers:
        tiers_data.append({
            "Faixa de Valor do Orcamento": t.description,
            "Prazo Medio Maximo Permitido": f"Ate {t.allowed_term_days} dias corridos",
        })
    st.dataframe(pd.DataFrame(tiers_data), hide_index=True, use_container_width=True)

# Expander 4: Exportacao de Arquivo Excel
with st.expander("Exportar Proposta Comercial (Excel)"):
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_exp_inst = pd.DataFrame([
            {
                "Nº Parcela": inst.number,
                "Data Vencimento": inst.due_date.strftime("%d/%m/%Y"),
                "Dias Corridos": inst.days,
                "Valor Parcela": inst.value,
                "Peso Financeiro": inst.factor,
                "Dias Ponderados": inst.weighted_days,
            }
            for inst in result.installments
        ])
        df_exp_inst.to_excel(writer, sheet_name="Grade de Parcelas", index=False)
        
        parecer_texto = (
            "VALOR DIVERGENTE" if has_value_mismatch 
            else ("APROVADO" if result.is_approved else "NAO PERMITIDO")
        )
        
        df_exp_summary = pd.DataFrame([
            {"Parametro": "Data do Fechamento", "Valor": result.closing_date.strftime("%d/%m/%Y")},
            {"Parametro": "Valor Total do Orcamento", "Valor": result.total_value},
            {"Parametro": "Valor da Entrada", "Valor": result.down_payment},
            {"Parametro": "Soma das Parcelas", "Valor": total_grid},
            {"Parametro": "Prazo Maximo Permitido (dias)", "Valor": result.allowed_term_days},
            {"Parametro": "Prazo Medio Ponderado (dias)", "Valor": result.weighted_average_term_days},
            {"Parametro": "Prazo Medio Simples (dias)", "Valor": result.simple_average_term_days},
            {"Parametro": "Data Media Ponderada", "Valor": result.weighted_average_date.strftime("%d/%m/%Y")},
            {"Parametro": "Parecer Comercial", "Valor": parecer_texto},
        ])
        df_exp_summary.to_excel(writer, sheet_name="Parecer Comercial", index=False)
    
    excel_buffer.seek(0)
    
    col_dl1, col_dl2 = st.columns([1, 3])
    with col_dl1:
        st.download_button(
            label="Baixar Planilha Excel (.xlsx)",
            data=excel_buffer,
            file_name=f"parecer_prazo_medio_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_dl2:
        st.caption("Planilha formatada contendo a grade e o parecer para arquivo ou anexo de proposta.")
