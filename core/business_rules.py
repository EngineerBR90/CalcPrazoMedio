"""
Regras de negócio e cálculos de prazo médio conforme a política comercial.
Reproduz e aprimora as validações da planilha original 'Condições negociadas.xls'.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional
import math


@dataclass
class PolicyTier:
    """Faixa da política comercial para concessão de prazo médio."""
    min_value: float
    max_value: float
    allowed_term_days: int
    description: str = ""


@dataclass
class Installment:
    """Dados consolidados de uma parcela."""
    number: int
    due_date: date
    days: int
    value: float
    factor: float  # Peso financeiro (valor / total)
    weighted_days: float  # factor * days


@dataclass
class CalculationResult:
    """Resultado completo da análise da proposta."""
    total_value: float
    down_payment: float
    closing_date: date
    installments: List[Installment]
    allowed_term_days: int
    weighted_average_term_days: float  # Prazo médio proporcional
    simple_average_term_days: float    # Prazo médio simples
    weighted_average_date: date        # Data de fechamento + prazo médio proporcional
    simple_average_date: date          # Data média simples das parcelas
    is_approved: bool                  # weighted_average_term_days <= allowed_term_days
    difference_days: float             # weighted_average_term_days - allowed_term_days
    suggested_min_down_payment: Optional[float] = None


def get_default_policy_tiers() -> List[PolicyTier]:
    """Retorna as faixas padrão extraídas da planilha original."""
    return [
        PolicyTier(min_value=0.0, max_value=400.0, allowed_term_days=30, description="R$ 0,00 a R$ 400,00"),
        PolicyTier(min_value=401.0, max_value=2000.0, allowed_term_days=30, description="R$ 401,00 a R$ 2.000,00"),
        PolicyTier(min_value=2001.0, max_value=6000.0, allowed_term_days=45, description="R$ 2.001,00 a R$ 6.000,00"),
        PolicyTier(min_value=6001.0, max_value=999999999.0, allowed_term_days=60, description="Acima de R$ 6.001,00"),
    ]


def get_allowed_term(total_value: float, policy_tiers: Optional[List[PolicyTier]] = None) -> int:
    """Determina o prazo médio máximo permitido para determinado valor total de orçamento."""
    tiers = policy_tiers or get_default_policy_tiers()
    for tier in tiers:
        if tier.min_value <= total_value <= tier.max_value:
            return tier.allowed_term_days
    # Fallback caso fora das faixas (assume a faixa mais alta se positivo)
    if total_value > 0 and tiers:
        return tiers[-1].allowed_term_days
    return 30


def generate_installments(
    closing_date: date,
    total_value: float,
    down_payment: float,
    num_installments: int,
    first_due_days: int = 30,
    interval_days: int = 30,
    custom_dates: Optional[List[date]] = None,
    custom_values: Optional[List[float]] = None,
) -> List[Installment]:
    """
    Gera as parcelas calculando dias corridos, valores rateados e pesos financeiros.
    """
    if num_installments <= 0:
        return []

    # Valida entrada
    down_payment = max(0.0, min(down_payment, total_value))

    # Determina datas de vencimento
    due_dates: List[date] = []
    if custom_dates and len(custom_dates) == num_installments:
        due_dates = custom_dates
    else:
        # Gera datas sequenciais padrão
        # Se houver entrada e first_due_days for definido, a 1ª parcela vence em closing_date + first_due_days
        current_date = closing_date + timedelta(days=first_due_days)
        due_dates.append(current_date)
        for _ in range(1, num_installments):
            current_date = current_date + timedelta(days=interval_days)
            due_dates.append(current_date)

    # Determina valores de cada parcela
    values: List[float] = []
    if custom_values and len(custom_values) == num_installments:
        values = custom_values
    else:
        # Lógica idêntica à planilha:
        if down_payment > 0:
            values.append(down_payment)
            remaining_installments = num_installments - 1
            if remaining_installments > 0:
                remaining_balance = total_value - down_payment
                regular_value = remaining_balance / remaining_installments
                values.extend([regular_value] * remaining_installments)
        else:
            # Sem entrada: rateio uniforme do total
            uniform_value = total_value / num_installments
            values = [uniform_value] * num_installments

    # Monta objetos de parcelas com cálculo dos pesos
    installments: List[Installment] = []
    for i in range(num_installments):
        d_date = due_dates[i]
        days = (d_date - closing_date).days
        val = values[i]
        factor = (val / total_value) if total_value > 0 else 0.0
        weighted_days = factor * days

        installments.append(
            Installment(
                number=i + 1,
                due_date=d_date,
                days=days,
                value=val,
                factor=factor,
                weighted_days=weighted_days,
            )
        )

    return installments


def suggest_minimum_down_payment(
    total_value: float,
    allowed_term_days: int,
    due_dates: List[date],
    closing_date: date,
) -> Optional[float]:
    """
    Calcula analiticamente a entrada mínima para que a condição seja aprovada mantendo as mesmas datas.
    """
    if len(due_dates) <= 1 or total_value <= 0:
        return None

    d1 = (due_dates[0] - closing_date).days
    remaining_days = [(d - closing_date).days for d in due_dates[1:]]
    avg_remaining_days = sum(remaining_days) / len(remaining_days)

    if avg_remaining_days <= d1:
        return None

    # Se mesmo sem entrada já aprova:
    if avg_remaining_days <= allowed_term_days:
        return 0.0

    # Fórmula: E = Total * (avg_rest - allowed) / (avg_rest - d1)
    min_entry = total_value * (avg_remaining_days - allowed_term_days) / (avg_remaining_days - d1)

    if min_entry > total_value:
        return total_value
    return max(0.0, min_entry)


def calculate_terms(
    closing_date: date,
    total_value: float,
    down_payment: float,
    installments: List[Installment],
    policy_tiers: Optional[List[PolicyTier]] = None,
) -> CalculationResult:
    """
    Consolida as métricas financeiras de prazo médio e gera o veredito de conformidade.
    """
    allowed_term = get_allowed_term(total_value, policy_tiers)

    if not installments:
        return CalculationResult(
            total_value=total_value,
            down_payment=down_payment,
            closing_date=closing_date,
            installments=[],
            allowed_term_days=allowed_term,
            weighted_average_term_days=0.0,
            simple_average_term_days=0.0,
            weighted_average_date=closing_date,
            simple_average_date=closing_date,
            is_approved=True,
            difference_days=0.0,
        )

    # 1. Prazo Médio Ponderado (Proporcional): Soma dos Fatores * Dias
    # Formula equivalente: sum(val_i * days_i) / total_value
    total_val = sum(inst.value for inst in installments) or total_value
    weighted_term = sum(inst.value * inst.days for inst in installments) / total_val if total_val > 0 else 0.0

    # 2. Prazo Médio Simples: Média aritmética simples dos dias
    simple_term = sum(inst.days for inst in installments) / len(installments)

    # 3. Datas Médias
    weighted_date = closing_date + timedelta(days=round(weighted_term))
    simple_date = closing_date + timedelta(days=round(simple_term))

    # 4. Veredito de Conformidade
    # Aprovado se Prazo Ponderado <= Prazo Permitido
    diff = weighted_term - allowed_term
    is_approved = weighted_term <= (allowed_term + 1e-4)  # Tolerância de arredondamento

    # 5. Entrada Mínima Sugerida (caso reprovado)
    suggested_down = None
    if not is_approved and len(installments) > 1:
        due_dates = [inst.due_date for inst in installments]
        suggested_down = suggest_minimum_down_payment(total_val, allowed_term, due_dates, closing_date)

    return CalculationResult(
        total_value=total_value,
        down_payment=down_payment,
        closing_date=closing_date,
        installments=installments,
        allowed_term_days=allowed_term,
        weighted_average_term_days=round(weighted_term, 2),
        simple_average_term_days=round(simple_term, 2),
        weighted_average_date=weighted_date,
        simple_average_date=simple_date,
        is_approved=is_approved,
        difference_days=round(diff, 2),
        suggested_min_down_payment=round(suggested_down, 2) if suggested_down is not None else None,
    )
