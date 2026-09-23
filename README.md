# ⚖️ Simulador de Prazo Médio Negociado

Aplicação web desenvolvida em **Streamlit** para cálculo, simulação e validação de prazos médios ponderados (proporcionais) em condições de pagamento comercial, de acordo com a política de crédito da empresa.

Reproduz fielmente e aprimora as regras contidas na planilha original `Condições negociadas.xls`.

---

## 🚀 Como Executar Localmente

1. **Clone ou acerte o diretório do projeto**:
   ```bash
   cd "Prazo médio"
   ```

2. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Inicie o aplicativo Streamlit**:
   ```bash
   streamlit run app.py
   ```

---

## ☁️ Como Publicar no Streamlit Community Cloud

O projeto foi construído rigorosamente dentro das especificações e convenções do **Streamlit Community Cloud**:

1. Suba esta pasta para um repositório no seu **GitHub** (ex: `seu-usuario/prazo-medio`).
2. Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login com seu GitHub.
3. Clique em **"New app"**.
4. Selecione:
   - **Repository**: `seu-usuario/prazo-medio`
   - **Branch**: `main` (ou `master`)
   - **Main file path**: `app.py`
5. Clique em **"Deploy"**.

Em menos de 1 minuto seu aplicativo estará online com link compartilhável e certificado SSL automático.

---

## 📊 Regras de Negócio e Cálculos

### 1. Política Comercial Padrão (Faixas de Orçamento)
| Faixa de Valor (De) | Até | Prazo Médio Permitido |
| :--- | :--- | :---: |
| R$ 0,00 | R$ 400,00 | **30 dias corridos** |
| R$ 401,00 | R$ 2.000,00 | **30 dias corridos** |
| R$ 2.001,00 | R$ 6.000,00 | **45 dias corridos** |
| R$ 6.001,00 a R$ 999.999,00+ | Acima | **60 dias corridos** |

### 2. Prazo Médio Ponderado (Proporcional)
O critério oficial de conformidade financeira pondera o prazo em dias corridos de cada parcela pelo seu peso financeiro sobre o total:

$$\text{Prazo Médio Ponderado} = \sum_{i=1}^{N} \left( \frac{\text{Valor}_i}{\text{Valor Total}} \times \text{Dias}_i \right)$$

### 3. Assistente de Entrada Mínima
Se uma proposta for bloqueada por excesso de prazo médio, o algoritmo calcula analiticamente o valor mínimo de entrada necessário para aprovação mantendo os mesmos vencimentos negociados com o cliente:

$$E_{\text{mínima}} = \text{Total} \times \frac{\bar{d}_{\text{resto}} - P_{\text{permitido}}}{\bar{d}_{\text{resto}} - d_1}$$

---

## 📁 Estrutura do Projeto

```text
Prazo médio/
├── .streamlit/
│   └── config.toml          # Tema visual moderno e opções de servidor
├── core/
│   ├── __init__.py
│   └── business_rules.py    # Motor financeiro, validações e otimizador
├── app.py                   # Aplicação Streamlit principal
├── requirements.txt         # Dependências do Streamlit Community Cloud
├── .gitignore               # Arquivos ignorados pelo Git
└── README.md                # Este documento
```
