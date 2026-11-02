"""计算画像：所有下游模块只吃这一份数据。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from profile.errors import ProfileError

RISK_TIERS = ("high", "mid", "low")
DEFAULT_ALLOCATION = {"high": 0.3, "mid": 0.5, "low": 0.2}
"""默认股/债/存款配比，见 docs/data-sources.md §2。"""


@dataclass(frozen=True, slots=True)
class PensionParams:
    """推导出的养老金精算参数，用户不直接填。"""

    years: int
    index: float
    account_balance: float
    base_wage: float


@dataclass(frozen=True, slots=True)
class Profile:
    age: int
    sex: str
    city: str
    retirement_age: int
    plan_until: int
    monthly_income: float
    monthly_expense: float
    assets: float
    debt: float
    retirement_expense: float
    travel_trips: float
    entertainment_monthly: float
    children: int
    pension: PensionParams
    allocations: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_ALLOCATION))

    def __post_init__(self) -> None:
        if not 18 <= self.age < self.plan_until:
            raise ProfileError("年龄需在 18 岁到规划终点之间。")
        if self.retirement_age < self.age:
            raise ProfileError("退休年龄不能早于当前年龄。")
        if self.retirement_age > self.plan_until:
            raise ProfileError("退休年龄不能晚于规划终点。")
        for name in ("monthly_income", "monthly_expense", "assets", "debt", "retirement_expense"):
            if getattr(self, name) < 0:
                raise ProfileError(f"{name} 不能为负。")
        total = sum(self.allocations.values())
        if abs(total - 1.0) > 1e-9:
            raise ProfileError(f"资产配比之和必须为 1，收到 {total:.4f}。")
        unknown = set(self.allocations) - set(RISK_TIERS)
        if unknown:
            raise ProfileError(f"未知风险档位：{sorted(unknown)}")

    @property
    def net_assets(self) -> float:
        return self.assets - self.debt
