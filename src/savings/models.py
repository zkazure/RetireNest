"""储蓄增长与目标倒推的数据结构。

金额单位为元；收益率与通胀率用百分数（5 表示 5%）；年限为整数。
默认口径与 `plan.engine` 一致：实际购买力、按年、期末投入。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

COMPOUNDING_ANNUAL = "annual"
COMPOUNDING_MONTHLY = "monthly"
TIMING_END = "end"
TIMING_BEGIN = "begin"

MAX_AMOUNT = 1_000_000_000.0
MIN_RETURN = -5.0
MAX_RETURN = 15.0
MIN_INFLATION = 0.0
MAX_INFLATION = 10.0
MIN_YEARS = 1
MAX_YEARS = 60


def _check_amount(name: str, value: float) -> None:
    if not math.isfinite(value) or not 0 <= value <= MAX_AMOUNT:
        raise ValueError(f"{name} 需在 0 到 {MAX_AMOUNT:,.0f} 元之间。")


def _check_assumptions(
    annual_return_pct: float,
    inflation_pct: float,
    years: int,
    compounding: str,
    timing: str,
) -> None:
    if not math.isfinite(annual_return_pct) or not MIN_RETURN <= annual_return_pct <= MAX_RETURN:
        raise ValueError(f"名义年回报率需在 {MIN_RETURN}% 到 {MAX_RETURN}% 之间。")
    if not math.isfinite(inflation_pct) or not MIN_INFLATION <= inflation_pct <= MAX_INFLATION:
        raise ValueError(f"年通胀率需在 {MIN_INFLATION}% 到 {MAX_INFLATION}% 之间。")
    if not MIN_YEARS <= years <= MAX_YEARS:
        raise ValueError(f"年限需在 {MIN_YEARS} 到 {MAX_YEARS} 年之间。")
    if compounding not in (COMPOUNDING_ANNUAL, COMPOUNDING_MONTHLY):
        raise ValueError(f"未知复利频率：{compounding}")
    if timing not in (TIMING_END, TIMING_BEGIN):
        raise ValueError(f"未知投入时点：{timing}")


@dataclass(frozen=True, slots=True)
class SavingsProjectInput:
    """给定当前储蓄、月投入和年限，预测未来余额。"""

    current_savings: float
    monthly_contribution: float
    annual_return_pct: float
    inflation_pct: float
    years: int
    compounding: str = COMPOUNDING_ANNUAL
    timing: str = TIMING_END

    def __post_init__(self) -> None:
        _check_amount("当前储蓄", self.current_savings)
        _check_amount("每月投入", self.monthly_contribution)
        _check_assumptions(
            self.annual_return_pct,
            self.inflation_pct,
            self.years,
            self.compounding,
            self.timing,
        )


@dataclass(frozen=True, slots=True)
class SavingsProjectResult:
    """余额同时给实际值与名义值；投入合计只算新增投入。"""

    future_balance_real: float
    future_balance_nominal: float
    total_contributions_real: float
    total_invested_real: float
    growth_real: float
    real_return_pct: float


@dataclass(frozen=True, slots=True)
class SavingsGoalInput:
    """给定目标金额，反推每月需要投入多少。"""

    target_amount: float
    current_savings: float
    annual_return_pct: float
    inflation_pct: float
    years: int
    compounding: str = COMPOUNDING_ANNUAL
    timing: str = TIMING_END

    def __post_init__(self) -> None:
        _check_amount("目标金额", self.target_amount)
        _check_amount("当前储蓄", self.current_savings)
        _check_assumptions(
            self.annual_return_pct,
            self.inflation_pct,
            self.years,
            self.compounding,
            self.timing,
        )


@dataclass(frozen=True, slots=True)
class SavingsGoalResult:
    """倒推结果；目标已被现有储蓄覆盖时，投入要求为 0。"""

    required_monthly_contribution_real: float
    required_annual_contribution_real: float
    projected_without_contribution_real: float
    shortfall_real: float
    real_return_pct: float
