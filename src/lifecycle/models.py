"""全周期仿真的输入输出。金额都是名义值，收益率是百分数。"""

from __future__ import annotations

from dataclasses import dataclass

WORKING = "工作"
RETIRED = "退休"


@dataclass(frozen=True, slots=True)
class YearRow:
    age: int
    phase: str
    income: float
    """主动收入：工资，退休后为 0。"""
    pension: float
    """养老金：退休后开始领取，工作期为 0。"""
    passive: float
    """被动收入：期初资产按组合实际收益率产生的收益。"""
    expense: float
    medical: float
    soft: float
    net: float
    assets: float
    real_return_pct: float

    @property
    def inflow(self) -> float:
        return self.income + self.pension + self.passive


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    rows: tuple[YearRow, ...]
    pension_monthly: float
    break_even_age: int | None
    depleted_age: int | None
    final_assets: float
    peak_assets: float
    retirement_assets: float
    """停止工作那一刻的资产：最后一个工作年年末。"""
    total_contributions: float
    """累计投入：起步净资产加工资、养老金，再减支出。"""
    total_returns: float
    """累计资产收益：逐年被动收入之和。终值 = 累计投入 + 累计收益。"""

    @property
    def total_income(self) -> float:
        return sum(row.inflow for row in self.rows)

    @property
    def total_expense(self) -> float:
        return sum(row.expense for row in self.rows)


@dataclass(frozen=True, slots=True)
class SimulationResult:
    paths: int
    success_rate: float
    depleted_p10: int | None
    depleted_median: int | None
    depleted_p90: int | None
    terminal_p10: float
    terminal_median: float
    terminal_p90: float
    affordable_monthly_expense: float
    """成功率不低于 90% 时能支撑的退休后月生活支出。"""
    affordable_working_expense: float
    """同一支出倍数下能支撑的工作期月生活支出。"""
    required_monthly_income: float | None
    """维持现有支出计划、成功率不低于 90% 所需的最低工作期月收入；超出上限时为 None。"""
