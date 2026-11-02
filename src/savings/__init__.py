"""savings：储蓄增长与目标倒推。

所有函数按实际购买力计算，默认按年、期末投入，与 `plan.engine` 一致。
"""

from savings.goal import required_contribution
from savings.models import (
    COMPOUNDING_ANNUAL,
    COMPOUNDING_MONTHLY,
    TIMING_BEGIN,
    TIMING_END,
    SavingsGoalInput,
    SavingsGoalResult,
    SavingsProjectInput,
    SavingsProjectResult,
)
from savings.projection import project
from savings.rates import annuity_factor, future_value, period_rate, real_rate

__all__ = [
    "COMPOUNDING_ANNUAL",
    "COMPOUNDING_MONTHLY",
    "TIMING_BEGIN",
    "TIMING_END",
    "SavingsGoalInput",
    "SavingsGoalResult",
    "SavingsProjectInput",
    "SavingsProjectResult",
    "annuity_factor",
    "future_value",
    "period_rate",
    "project",
    "real_rate",
    "required_contribution",
]
