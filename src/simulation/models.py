"""蒙特卡洛与提取率共用的输入输出。

所有金额按今天的购买力（实际值）；收益率与通胀率用百分数。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_AMOUNT = 1_000_000_000.0
MIN_RETURN = -5.0
MAX_RETURN = 15.0
MIN_INFLATION = 0.0
MAX_INFLATION = 10.0
MAX_VOLATILITY = 40.0
MIN_PATHS = 100
MAX_PATHS = 20_000
MAX_SEED = 2**31 - 1


def _check_amount(name: str, value: float) -> None:
    if not math.isfinite(value) or not 0 <= value <= MAX_AMOUNT:
        raise ValueError(f"{name} 需在 0 到 {MAX_AMOUNT:,.0f} 元之间。")


def _check_years(name: str, value: int) -> None:
    if not 1 <= value <= 50:
        raise ValueError(f"{name} 需在 1 到 50 年之间。")


def _check_retirement_years(value: int) -> None:
    if not 1 <= value <= 60:
        raise ValueError("退休后年数需在 1 到 60 年之间。")


def _check_assumptions(
    annual_return_pct: float,
    volatility_pct: float,
    inflation_pct: float,
) -> None:
    if not math.isfinite(annual_return_pct) or not MIN_RETURN <= annual_return_pct <= MAX_RETURN:
        raise ValueError(f"名义年回报率需在 {MIN_RETURN}% 到 {MAX_RETURN}% 之间。")
    if not math.isfinite(volatility_pct) or not 0 <= volatility_pct <= MAX_VOLATILITY:
        raise ValueError(f"年波动率需在 0% 到 {MAX_VOLATILITY}% 之间。")
    if not math.isfinite(inflation_pct) or not MIN_INFLATION <= inflation_pct <= MAX_INFLATION:
        raise ValueError(f"年通胀率需在 {MIN_INFLATION}% 到 {MAX_INFLATION}% 之间。")


def _check_paths(paths: int, seed: int) -> None:
    if not MIN_PATHS <= paths <= MAX_PATHS:
        raise ValueError(f"路径数需在 {MIN_PATHS} 到 {MAX_PATHS} 之间。")
    if not 0 <= seed <= MAX_SEED:
        raise ValueError(f"随机种子需在 0 到 {MAX_SEED} 之间。")


@dataclass(frozen=True, slots=True)
class MonteCarloInput:
    """积累期加退休期的路径模拟输入。"""

    current_savings: float
    monthly_contribution: float
    years_to_retirement: int
    retirement_years: int
    annual_return_pct: float
    volatility_pct: float
    inflation_pct: float
    annual_retirement_expense: float
    monthly_pension: float = 0.0
    paths: int = 2000
    seed: int = 42

    def __post_init__(self) -> None:
        _check_amount("当前储蓄", self.current_savings)
        _check_amount("每月投入", self.monthly_contribution)
        _check_amount("退休后年支出", self.annual_retirement_expense)
        _check_amount("月养老金", self.monthly_pension)
        _check_years("距离退休年数", self.years_to_retirement)
        _check_retirement_years(self.retirement_years)
        if self.years_to_retirement + self.retirement_years > 100:
            raise ValueError("距离退休年数与退休后年数合计不能超过 100 年。")
        _check_assumptions(
            self.annual_return_pct,
            self.volatility_pct,
            self.inflation_pct,
        )
        _check_paths(self.paths, self.seed)


@dataclass(frozen=True, slots=True)
class BalancePercentile:
    """某一年的余额分位；year=0 表示现在。"""

    year: int
    p10: float
    p50: float
    p90: float


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    """路径模拟的汇总结果。

    `success_rate` 是未耗尽路径的占比（0–100），不是概率保证；
    `depletion_year_percentiles` 在没有任何路径耗尽时为空。
    """

    success_rate: float
    failed_paths: int
    terminal_balance_percentiles: dict[str, float]
    depletion_year_percentiles: dict[str, float]
    balance_percentiles: tuple[BalancePercentile, ...]


@dataclass(frozen=True, slots=True)
class WithdrawalInput:
    """已有余额时，反推可安全提取的比例。"""

    retirement_savings: float
    retirement_years: int
    annual_return_pct: float
    volatility_pct: float
    inflation_pct: float
    target_success_rate: float = 90.0
    paths: int = 2000
    seed: int = 42

    def __post_init__(self) -> None:
        _check_amount("退休时可动用储蓄", self.retirement_savings)
        _check_retirement_years(self.retirement_years)
        _check_assumptions(
            self.annual_return_pct,
            self.volatility_pct,
            self.inflation_pct,
        )
        if not 50 <= self.target_success_rate <= 99.9:
            raise ValueError("目标成功率需在 50% 到 99.9% 之间。")
        _check_paths(self.paths, self.seed)


@dataclass(frozen=True, slots=True)
class WithdrawalResult:
    """安全提取率与对应现金流；比例用百分数。"""

    safe_withdrawal_rate_pct: float
    annual_withdrawal_real: float
    monthly_withdrawal_real: float
    success_rate_at_rate: float
    depletion_year_percentiles: dict[str, float]
