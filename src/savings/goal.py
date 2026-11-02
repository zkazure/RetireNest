"""目标倒推：给定目标金额，算每月需要投入多少。"""

from __future__ import annotations

from savings.models import (
    COMPOUNDING_MONTHLY,
    SavingsGoalInput,
    SavingsGoalResult,
)
from savings.rates import annuity_factor, period_rate, real_rate


def required_contribution(data: SavingsGoalInput) -> SavingsGoalResult:
    """反推达到目标所需的月投入；目标已被现有储蓄覆盖时返回 0。

    计算顺序与 `plan.required_monthly_saving` 保持一致：
    `(目标 - 现有储蓄的未来值) / 年金系数 / 12`，便于交叉对拍。
    """
    real = real_rate(data.annual_return_pct, data.inflation_pct)
    monthly = data.compounding == COMPOUNDING_MONTHLY
    if monthly:
        rate = period_rate(real, 12)
        periods = data.years * 12
    else:
        rate = real
        periods = data.years

    projected = data.current_savings * (1 + rate) ** periods
    shortfall = max(0.0, data.target_amount - projected)
    if shortfall == 0:
        required_monthly = 0.0
    else:
        per_period = shortfall / annuity_factor(rate, periods, data.timing)
        required_monthly = per_period if monthly else per_period / 12

    return SavingsGoalResult(
        required_monthly_contribution_real=required_monthly,
        required_annual_contribution_real=required_monthly * 12,
        projected_without_contribution_real=projected,
        shortfall_real=shortfall,
        real_return_pct=real * 100,
    )
