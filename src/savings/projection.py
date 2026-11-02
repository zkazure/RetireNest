"""储蓄增长预测：给定当前储蓄、每月投入、收益率和年限，算未来余额。"""

from __future__ import annotations

from savings.models import (
    COMPOUNDING_MONTHLY,
    SavingsProjectInput,
    SavingsProjectResult,
)
from savings.rates import future_value, period_rate, real_rate


def project(data: SavingsProjectInput) -> SavingsProjectResult:
    """按月或按年复利，预测退休时的实际余额与名义余额。

    `monthly_contribution` 与 `current_savings` 都按今天的购买力填写；
    名义余额只是把实际余额按通胀折算回去，不改变实际缴费的假设。
    """
    real = real_rate(data.annual_return_pct, data.inflation_pct)
    if data.compounding == COMPOUNDING_MONTHLY:
        rate = period_rate(real, 12)
        periods = data.years * 12
        contribution = data.monthly_contribution
    else:
        rate = real
        periods = data.years
        contribution = data.monthly_contribution * 12

    future_real = future_value(
        data.current_savings,
        rate,
        periods,
        contribution,
        data.timing,
    )
    inflation_factor = (1 + data.inflation_pct / 100) ** data.years
    total_contributions = data.monthly_contribution * 12 * data.years
    total_invested = data.current_savings + total_contributions

    return SavingsProjectResult(
        future_balance_real=future_real,
        future_balance_nominal=future_real * inflation_factor,
        total_contributions_real=total_contributions,
        total_invested_real=total_invested,
        growth_real=future_real - total_invested,
        real_return_pct=real * 100,
    )
