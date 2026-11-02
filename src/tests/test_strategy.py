"""人生策略预设的测试。"""

from __future__ import annotations

from datetime import date
from profile.build import build_profile
from profile.schema import Profile

import pytest

from strategy import PRESET_IDS, PRESETS, StrategyError, apply, get_preset


def birth_for(age: int) -> date:
    today = date.today()
    return today.replace(year=today.year - age)


def _profile(**overrides) -> Profile:
    base = {
        "age": 35,
        "sex": "男",
        "city": "上海",
        "income_tier": "20k30k",
        "expense_tier": "10k15k",
        "asset_tier": "100w200w",
        "debt_tier": "none",
        "retirement_expense_tier": "6k10k",
        "travel_tier": "once",
        "entertainment_tier": "mid",
        "children_tier": "none",
        "birth_date": birth_for(35),
    }
    base.update(overrides)
    return build_profile(**base)


def test_五个预设齐全且标签不重复():
    assert set(PRESETS) == set(PRESET_IDS)
    labels = [preset.label for preset in PRESETS.values()]
    assert len(labels) == len(set(labels))


def test_未知策略报错():
    with pytest.raises(StrategyError):
        get_preset("unknown")


@pytest.mark.parametrize("preset_id", PRESET_IDS)
def test_预设都能套到画像上(preset_id):
    profile = _profile()
    variant = apply(get_preset(preset_id), profile)
    assert variant is not profile
    assert sum(variant.allocations.values()) == pytest.approx(1.0)
    assert variant.retirement_age >= profile.age


def test_丁克不育儿且提前退休():
    profile = _profile(children_tier="one")
    variant = apply(get_preset("dink"), profile)
    assert variant.children == 0
    assert variant.retirement_age == profile.retirement_age - 3


def test_FIRE_更早退休且支出更低():
    profile = _profile()
    variant = apply(get_preset("fire"), profile)
    assert variant.retirement_age < profile.retirement_age
    assert variant.retirement_expense < profile.retirement_expense
    assert variant.allocations["high"] > profile.allocations["high"]


def test_养娃延后退休且支出更高():
    profile = _profile()
    variant = apply(get_preset("one_child"), profile)
    assert variant.children == 1
    assert variant.retirement_age > profile.retirement_age
    assert variant.retirement_expense > profile.retirement_expense


def test_低耗稳健压缩支出并降低风险():
    profile = _profile()
    variant = apply(get_preset("frugal"), profile)
    assert variant.travel_trips == 0
    assert variant.entertainment_monthly < profile.entertainment_monthly
    assert variant.allocations["high"] == 0


def test_退休年龄被夹在当前年龄与规划终点之间():
    profile = _profile(age=60, children_tier="none", birth_date=birth_for(60))
    variant = apply(get_preset("fire"), profile)
    assert profile.age <= variant.retirement_age < profile.plan_until
