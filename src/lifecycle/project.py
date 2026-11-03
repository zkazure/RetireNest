"""确定性全周期推演：工作期收钱、退休期花钱，逐年滚动资产。"""

from __future__ import annotations

from profile.schema import Profile

from lifecycle.models import RETIRED, WORKING, LifecycleResult, YearRow
from living.constants import CHILD_BIRTH_AGE
from living.extras import soft_annual, upbringing_annual
from medical.tri_state import expected_annual
from pension import BasicPensionInput
from pension import calculate as calculate_pension
from portfolio import combine

INFLATION_PCT = 2.5
"""长期通胀中枢，沿用 living 的口径，见 docs/data-sources.md。"""

SECOND_CHILD_GAP = 3
"""第二个孩子按相差三岁估，养育支出按 60% 系数。"""

PENSION_TABLE_MIN_AGE = 40
PENSION_TABLE_MAX_AGE = 70
"""计发月数表覆盖 40–70 周岁，表外年龄夹到边界，见 pension.params。"""


def pension_monthly(profile: Profile) -> float:
    """退休后每月养老金，复用 pension 域的口径；计发月数按实际退休年龄。"""
    age = min(
        max(profile.retirement_age, PENSION_TABLE_MIN_AGE),
        PENSION_TABLE_MAX_AGE,
    )
    result = calculate_pension(
        BasicPensionInput(
            birth_date=profile.birth_date,
            gender=profile.sex,
            contribution_years=profile.pension.years,
            average_index=f"{profile.pension.index:.4f}",
            account_balance=f"{profile.pension.account_balance:.2f}",
            calculation_base=f"{profile.pension.base_wage:.2f}",
            category=profile.category,
            retirement_age_months=age * 12,
        )
    )
    return float(result.total)


def real_return_pct(profile: Profile, inflation_pct: float = INFLATION_PCT) -> float:
    assumption = combine(profile.allocations)
    return ((1 + assumption.annual_return_pct / 100) / (1 + inflation_pct / 100) - 1) * 100


def child_ages(profile: Profile, age: int) -> tuple[int, ...]:
    """按初育年龄 30 岁推算孩子年龄；还没出生记为 -1。"""
    if profile.children <= 0:
        return ()
    first = age - CHILD_BIRTH_AGE
    if profile.children == 1:
        return (first,)
    return (first, first - SECOND_CHILD_GAP)


def yearly_soft(profile: Profile, age: int) -> float:
    ages = [a for a in child_ages(profile, age) if a >= 0]
    total = soft_annual(
        entertainment_monthly=profile.entertainment_monthly,
        trips=profile.travel_trips,
        child_age=ages[0] if ages else None,
    )
    if len(ages) > 1:
        total += upbringing_annual(ages[1]) * 0.6
    return total


def project(profile: Profile, inflation_pct: float = INFLATION_PCT) -> LifecycleResult:
    rate = real_return_pct(profile, inflation_pct)
    pension = pension_monthly(profile)
    assets = float(profile.net_assets)
    start_assets = assets
    retirement_assets = start_assets
    total_contributions = start_assets
    total_returns = 0.0
    peak = assets
    rows: list[YearRow] = []
    depleted_age: int | None = None
    break_even_age: int | None = None

    for age in range(profile.age, profile.plan_until):
        working = age < profile.retirement_age
        income = profile.monthly_income * 12 if working else 0.0
        pension_annual = 0.0 if working else pension * 12
        base_expense = (
            profile.monthly_expense * 12 if working else profile.retirement_expense * 12
        )
        medical = expected_annual(age, profile.sex)
        soft = yearly_soft(profile, age)
        expense = base_expense + medical + soft
        passive = assets * rate / 100
        net = income + pension_annual + passive - expense
        total_returns += passive
        total_contributions += income + pension_annual - expense
        assets = assets + net
        if age == profile.retirement_age - 1:
            retirement_assets = assets
        if net < 0 and break_even_age is None:
            break_even_age = age
        if assets < 0 and depleted_age is None:
            depleted_age = age
        peak = max(peak, assets)
        rows.append(
            YearRow(
                age=age,
                phase=WORKING if working else RETIRED,
                income=round(income, 2),
                pension=round(pension_annual, 2),
                passive=round(passive, 2),
                expense=round(expense, 2),
                medical=round(medical, 2),
                soft=round(soft, 2),
                net=round(net, 2),
                assets=round(assets, 2),
                real_return_pct=round(rate, 4),
            )
        )

    return LifecycleResult(
        rows=tuple(rows),
        pension_monthly=round(pension, 2),
        break_even_age=break_even_age,
        depleted_age=depleted_age,
        final_assets=rows[-1].assets if rows else round(assets, 2),
        peak_assets=round(peak, 2),
        retirement_assets=round(retirement_assets, 2),
        total_contributions=round(total_contributions, 2),
        total_returns=round(total_returns, 2),
    )
