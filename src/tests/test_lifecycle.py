"""全周期仿真与策略对比的测试。"""

from __future__ import annotations

from datetime import date
from profile.build import build_profile

import pytest

from lifecycle import compare, project, simulate
from lifecycle.errors import LifecycleError
from lifecycle.project import real_return_pct


def birth_for(age: int) -> date:
    today = date.today()
    return today.replace(year=today.year - age)


def make_profile(**overrides):
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


def test_逐年行数与阶段():
    profile = make_profile()
    result = project(profile)
    assert len(result.rows) == profile.plan_until - profile.age
    assert result.rows[0].age == profile.age
    working = [row for row in result.rows if row.phase == "工作"]
    retired = [row for row in result.rows if row.phase == "退休"]
    assert len(working) == profile.retirement_age - profile.age
    assert all(row.age >= profile.retirement_age for row in retired)


def test_退休后主动收入为0且改领养老金():
    profile = make_profile()
    result = project(profile)
    at_retirement = next(row for row in result.rows if row.age == profile.retirement_age)
    assert at_retirement.income == 0
    assert at_retirement.pension == pytest.approx(result.pension_monthly * 12, rel=1e-3)
    assert at_retirement.pension < profile.monthly_income * 12


def test_被动收入按期初资产与实际收益率计算():
    profile = make_profile()
    result = project(profile)
    rate = real_return_pct(profile)
    row = result.rows[0]
    assert row.passive == pytest.approx(profile.net_assets * rate / 100, rel=1e-6)
    assert row.inflow == pytest.approx(row.income + row.pension + row.passive)
    assert row.passive > 0


def test_资产收益不改变资产轨迹():
    """被动收入只是把复利拆出来展示，资产必须与旧的复利写法逐位一致。"""
    profile = make_profile()
    result = project(profile)
    rate = real_return_pct(profile)
    assets = float(profile.net_assets)
    for row in result.rows:
        assets = assets * (1 + rate / 100) + (row.income + row.pension - row.expense)
        assert row.assets == pytest.approx(round(assets, 2), abs=0.01)


def test_结余按主动收入加被动收入计算():
    profile = make_profile(income_tier="gt50k", asset_tier="gt500w", expense_tier="lt2k")
    result = project(profile)
    assert result.break_even_age is None
    assert all(row.net == pytest.approx(row.inflow - row.expense, abs=0.02) for row in result.rows)


def test_退休后依靠养老金与资产收益():
    profile = make_profile()
    result = project(profile)
    retired = [row for row in result.rows if row.age >= profile.retirement_age]
    assert all(row.income == 0 for row in retired)
    assert all(row.pension == pytest.approx(result.pension_monthly * 12, rel=1e-3) for row in retired)
    assert all(row.passive > 0 for row in retired)
    assert result.rows[-1].passive > result.rows[0].passive


def test_工作期不领养老金():
    profile = make_profile()
    result = project(profile)
    working = [row for row in result.rows if row.phase == "工作"]
    assert all(row.pension == 0 for row in working)
    assert all(row.income == pytest.approx(profile.monthly_income * 12) for row in working)


def test_支出包含医疗与软性():
    profile = make_profile()
    result = project(profile)
    row = result.rows[0]
    assert row.medical > 0
    assert row.soft > 0
    assert row.expense == pytest.approx(
        profile.monthly_expense * 12 + row.medical + row.soft, rel=1e-6
    )


def test_资产不足时标记破产年龄():
    profile = make_profile(asset_tier="lt10w", income_tier="lt5k", expense_tier="15k25k")
    result = project(profile)
    assert result.depleted_age is not None
    assert result.depleted_age >= profile.age


def test_没有赤字时破产年龄为空():
    profile = make_profile(income_tier="gt50k", asset_tier="gt500w", expense_tier="lt2k")
    result = project(profile)
    assert result.depleted_age is None


def test_仿真固定种子可复现():
    profile = make_profile()
    first = simulate(profile, paths=200, seed=7)
    second = simulate(profile, paths=200, seed=7)
    assert first == second
    assert 0 <= first.success_rate <= 1


def test_路径数越界报错():
    profile = make_profile()
    with pytest.raises(LifecycleError):
        simulate(profile, paths=10)


def test_成功率低时可支撑支出被下调():
    profile = make_profile(asset_tier="lt10w", income_tier="lt5k", expense_tier="15k25k")
    result = simulate(profile, paths=200)
    assert result.success_rate < 1
    assert result.affordable_monthly_expense <= profile.retirement_expense


def test_策略对比覆盖五个预设():
    summaries = compare(make_profile(), paths=100)
    assert len(summaries) == 5
    labels = [item.label for item in summaries]
    assert "丁克" in labels and "早退 FIRE" in labels
    fire = next(item for item in summaries if item.preset_id == "fire")
    steady = next(item for item in summaries if item.preset_id == "steady")
    assert fire.retirement_age < steady.retirement_age
