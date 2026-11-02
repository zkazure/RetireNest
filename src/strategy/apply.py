"""把预设套到画像上，得到可比较的变体。"""

from __future__ import annotations

from dataclasses import replace
from profile.errors import ProfileError
from profile.schema import Profile
from profile.tiers import ENTERTAINMENT

from strategy.errors import StrategyError
from strategy.presets import Preset


def apply(preset: Preset, profile: Profile) -> Profile:
    """返回套用预设后的新画像；原画像不变。"""
    retirement_age = max(profile.age + 1, profile.retirement_age + preset.retirement_age_delta)
    retirement_age = min(retirement_age, profile.plan_until - 1)
    children = profile.children if preset.children is None else preset.children
    entertainment = profile.entertainment_monthly
    if preset.entertainment is not None:
        entertainment = ENTERTAINMENT.get(preset.entertainment).amount
    travel = profile.travel_trips if preset.travel_trips is None else preset.travel_trips
    try:
        return replace(
            profile,
            retirement_age=retirement_age,
            retirement_expense=round(profile.retirement_expense * preset.retirement_expense_factor, 2),
            travel_trips=travel,
            entertainment_monthly=entertainment,
            children=children,
            allocations=dict(preset.allocation),
        )
    except ProfileError as exc:
        raise StrategyError(f"策略 {preset.id} 套用后画像不合法：{exc}") from exc
