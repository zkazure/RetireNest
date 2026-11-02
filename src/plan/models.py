"""基础退休规划的数据结构。

金额单位为元，`nominal_return` 与 `inflation` 以百分数表示（3 表示 3%）。
本期只覆盖 12 个基础字段；医疗、养老、存款与生活支出由各自命令测算。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlanInput:
    """参与基础测算的标准化输入。"""

    city: str
    age: int
    retirement_age: int
    life_expectancy: int
    monthly_income: float
    monthly_expense: float
    assets: float
    debt: float
    retirement_expense: float
    monthly_pension: float
    nominal_return: float
    inflation: float


@dataclass(frozen=True, slots=True)
class ProjectionPoint:
    """某一周岁年末的资产余额；负值表示资金不足。"""

    age: int
    assets: float


@dataclass(frozen=True, slots=True)
class PlanResult:
    """基础测算结果，字段含义与前端 PlanResult 一致。"""

    years_to_retirement: int
    retirement_years: int
    real_return: float
    monthly_surplus: float
    target: float
    projected: float
    gap: float
    coverage: float
    required_monthly_saving: float
    points: tuple[ProjectionPoint, ...]
    depleted_age: int | None


@dataclass(frozen=True, slots=True)
class Scenario:
    """只调整名义年回报的情景结果。"""

    id: str
    label: str
    nominal_return: float
    target: float
    projected: float
    gap: float


@dataclass(frozen=True, slots=True)
class FieldError:
    """可定位到表单字段的校验错误。"""

    field: str
    message: str
