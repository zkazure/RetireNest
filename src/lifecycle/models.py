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
    expense: float
    medical: float
    soft: float
    net: float
    assets: float
    real_return_pct: float


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    rows: tuple[YearRow, ...]
    pension_monthly: float
    break_even_age: int | None
    depleted_age: int | None
    final_assets: float
    peak_assets: float

    @property
    def total_income(self) -> float:
        return sum(row.income for row in self.rows)

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
    """成功率不低于 90% 时能支撑的退休后月支出。"""
