"""profile：把选择题解析成计算画像。

页面只收集选项；`tiers` 给出每个选项对应的数字，`derive` 由选项推导养老金
参数与默认年龄，`build` 汇总成冻结的 `Profile`。下游模块只依赖 `Profile`。
"""

from profile.build import build_profile, tier_amount
from profile.errors import ProfileError
from profile.schema import DEFAULT_ALLOCATION, RISK_TIERS, PensionParams, Profile

__all__ = [
    "DEFAULT_ALLOCATION",
    "RISK_TIERS",
    "PensionParams",
    "Profile",
    "ProfileError",
    "build_profile",
    "tier_amount",
]
