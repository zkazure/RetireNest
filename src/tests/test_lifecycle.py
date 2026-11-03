"""全周期仿真与策略对比的测试。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from profile.build import build_profile
from profile.derive import account_balance, contribution_index

import pytest

from lifecycle import compare, project, simulate
from lifecycle.errors import LifecycleError
from lifecycle.project import pension_monthly, real_return_pct
from pension import BasicPensionInput, calculate


def with_income(profile, monthly_income):
    """按给定月收入重算养老金参数，得到一份候选画像。"""
    params = profile.pension
    return replace(
        profile,
        monthly_income=monthly_income,
        pension=replace(
            params,
            index=contribution_index(monthly_income, params.base_wage),
            account_balance=account_balance(monthly_income, params.years),
        ),
    )


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


def test_仿真流入包含养老金():
    """退休期的流入是养老金，而不是 0；否则与确定性推演互相矛盾。"""
    profile = make_profile(
        age=60,
        income_tier="gt50k",
        expense_tier="lt2k",
        asset_tier="0",
        retirement_expense_tier="lt2k",
        retirement_age=60,
        birth_date=birth_for(60),
    )
    result = simulate(profile, paths=200)
    assert result.success_rate == 1


def test_所需收入在九成成功率处收敛():
    profile = make_profile(asset_tier="lt10w", income_tier="lt5k", expense_tier="15k25k")
    result = simulate(profile, paths=400)
    need = result.required_monthly_income
    assert need is not None and need > 0
    assert simulate(with_income(profile, need + 1), paths=400).success_rate >= 0.9
    assert simulate(with_income(profile, need * 0.95), paths=400).success_rate < 0.9


def test_当前收入充足时所需收入不高于当前收入():
    profile = make_profile()
    result = simulate(profile, paths=200)
    assert result.required_monthly_income is not None
    assert result.required_monthly_income <= profile.monthly_income


def test_可支撑支出按同一比例缩放():
    profile = make_profile()
    result = simulate(profile, paths=200)
    work = result.affordable_working_expense / profile.monthly_expense
    retired = result.affordable_monthly_expense / profile.retirement_expense
    assert work == pytest.approx(retired, rel=1e-3)


def test_关闭所需收入求解时返回空():
    result = simulate(make_profile(), paths=100, required=False)
    assert result.required_monthly_income is None


def test_策略对比覆盖五个预设():
    summaries = compare(make_profile(), paths=100)
    assert len(summaries) == 5
    labels = [item.label for item in summaries]
    assert "丁克" in labels and "早退 FIRE" in labels
    fire = next(item for item in summaries if item.preset_id == "fire")
    steady = next(item for item in summaries if item.preset_id == "steady")
    assert fire.retirement_age < steady.retirement_age

def expected_pension(profile, age_months: int) -> float:
    params = profile.pension
    result = calculate(
        BasicPensionInput(
            birth_date=profile.birth_date,
            gender=profile.sex,
            contribution_years=params.years,
            average_index=f"{params.index:.4f}",
            account_balance=f"{params.account_balance:.2f}",
            calculation_base=f"{params.base_wage:.2f}",
            category=profile.category,
            retirement_age_months=age_months,
        )
    )
    return float(result.total)


def test_养老金按实际退休年龄计发():
    profile = make_profile(retirement_age=60)
    assert pension_monthly(profile) == pytest.approx(expected_pension(profile, 60 * 12))


def test_表外退休年龄夹到计发月数表边界():
    profile = make_profile(age=30, birth_date=birth_for(30), retirement_age=30)
    assert pension_monthly(profile) == pytest.approx(expected_pension(profile, 40 * 12))


def test_提前退休的养老金低于按法定年龄计发():
    early = pension_monthly(make_profile(retirement_age=60))
    statutory = pension_monthly(make_profile(retirement_age=63))
    assert early < statutory


def test_退休时资产等于最后一个工作年年末():
    profile = make_profile()
    result = project(profile)
    row = next(row for row in result.rows if row.age == profile.retirement_age - 1)
    assert result.retirement_assets == row.assets


def test_当年退休时退休资产等于起步净资产():
    profile = make_profile(age=60, birth_date=birth_for(60), retirement_age=60)
    result = project(profile)
    assert result.retirement_assets == pytest.approx(profile.net_assets)


def test_终值等于累计投入加累计收益():
    result = project(make_profile())
    assert result.final_assets == pytest.approx(
        result.total_contributions + result.total_returns, abs=0.05
    )
