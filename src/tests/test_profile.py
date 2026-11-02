"""档位表、推导与画像的测试。"""

from __future__ import annotations

from datetime import date
from profile import tiers
from profile.build import build_profile, tier_amount
from profile.derive import (
    MAX_CONTRIBUTION_YEARS,
    MAX_INDEX,
    MIN_INDEX,
    account_balance,
    city_base_wage,
    contribution_index,
    contribution_years,
    realistic_plan_until,
    statutory_retirement_age,
)
from profile.errors import ProfileError
from profile.schema import DEFAULT_ALLOCATION, PensionParams, Profile

import pytest

TABLES = (
    tiers.INCOME,
    tiers.EXPENSE,
    tiers.ASSETS,
    tiers.DEBT,
    tiers.RETIRE_EXPENSE,
    tiers.RETIRE_AGE,
    tiers.PLAN_UNTIL,
    tiers.TRAVEL,
    tiers.ENTERTAINMENT,
    tiers.CHILDREN,
    tiers.LIVING_LEVEL,
)


@pytest.mark.parametrize("table", TABLES, ids=[t.name for t in TABLES])
def test_档位取值不重复且落在区间内(table):
    values = [tier.value for tier in table.tiers]
    assert len(values) == len(set(values)), f"{table.name} 有重复选项"
    for tier in table.tiers:
        if tier.low is not None and tier.high is not None:
            assert tier.low <= tier.amount <= tier.high, f"{table.name} {tier.value} 取值越界"


@pytest.mark.parametrize("table", TABLES, ids=[t.name for t in TABLES])
def test_未知选项报错(table):
    with pytest.raises(ProfileError):
        table.get("不存在的选项")


def test_缴费年限按退休年龄算并封顶():
    assert contribution_years(30) == 8
    assert contribution_years(60) == MAX_CONTRIBUTION_YEARS
    assert contribution_years(70) == MAX_CONTRIBUTION_YEARS


def test_缴费年限要求退休晚于起缴():
    with pytest.raises(ProfileError):
        contribution_years(20)


def test_缴费指数按社平工资折算并夹紧():
    assert contribution_index(10_000, 10_000) == pytest.approx(1.0)
    assert contribution_index(3_000, 10_000) == pytest.approx(MIN_INDEX)
    assert contribution_index(50_000, 10_000) == pytest.approx(MAX_INDEX)


def test_个人账户余额随年限与利率增长():
    low = account_balance(10_000, 10)
    high = account_balance(10_000, 20)
    assert 0 < low < high
    assert account_balance(10_000, 10, rate=0) == pytest.approx(10_000 * 12 * 0.08 * 10)


@pytest.mark.parametrize(
    ("birth", "gender", "category", "expected"),
    [
        (date(1965, 1, 1), "男", None, 60),
        (date(1990, 1, 1), "男", None, 63),
        (date(1970, 1, 1), "女", "管理技术", 55),
        (date(1990, 1, 1), "女", "管理技术", 58),
        (date(1975, 1, 1), "女", "工人", 50),
        (date(1990, 1, 1), "女", "工人", 55),
    ],
)
def test_法定退休年龄(birth, gender, category, expected):
    assert statutory_retirement_age(birth, gender, category) == expected


def test_规划终点取寿命分位():
    age = realistic_plan_until(35, "男")
    assert 75 <= age <= 100


def test_城市计发基数按分级缩放():
    assert city_base_wage("上海") > city_base_wage("成都") > city_base_wage("兰州")
    assert city_base_wage("不存在的城市") == city_base_wage("兰州")


def test_由选项构建画像():
    profile = build_profile(
        age=35,
        sex="男",
        city="上海",
        income_tier="20k30k",
        expense_tier="10k15k",
        asset_tier="100w200w",
        debt_tier="none",
        retirement_expense_tier="6k10k",
        travel_tier="twice",
        entertainment_tier="mid",
        children_tier="one",
        birth_date=date(1991, 3, 1),
    )
    assert profile.monthly_income == pytest.approx(25_000)
    assert profile.monthly_expense == pytest.approx(12_500)
    assert profile.assets == pytest.approx(1_500_000)
    assert profile.children == 1
    assert profile.travel_trips == 2
    assert profile.retirement_age == 63
    assert profile.pension.years == 35
    assert profile.allocations == DEFAULT_ALLOCATION


def test_缺出生日期且没给退休年龄时报错():
    with pytest.raises(ProfileError):
        build_profile(
            age=35,
            sex="男",
            city="上海",
            income_tier="20k30k",
            expense_tier="10k15k",
            asset_tier="100w200w",
            debt_tier="none",
            retirement_expense_tier="6k10k",
            travel_tier="twice",
            entertainment_tier="mid",
            children_tier="one",
        )


def test_配比之和不为一报错():
    with pytest.raises(ProfileError):
        Profile(
            age=35,
            sex="男",
            city="上海",
            retirement_age=60,
            plan_until=85,
            monthly_income=10_000,
            monthly_expense=5_000,
            assets=0,
            debt=0,
            retirement_expense=4_000,
            travel_trips=0,
            entertainment_monthly=0,
            children=0,
            pension=PensionParams(30, 1.0, 0, 8_000),
            allocations={"high": 0.5, "mid": 0.5, "low": 0.5},
        )


def test_退休早于当前年龄报错():
    with pytest.raises(ProfileError):
        Profile(
            age=60,
            sex="男",
            city="上海",
            retirement_age=55,
            plan_until=85,
            monthly_income=10_000,
            monthly_expense=5_000,
            assets=0,
            debt=0,
            retirement_expense=4_000,
            travel_trips=0,
            entertainment_monthly=0,
            children=0,
            pension=PensionParams(30, 1.0, 0, 8_000),
        )


def test_选项值转数值():
    assert tier_amount(tiers.INCOME, "12k20k") == pytest.approx(16_000)
    with pytest.raises(ProfileError):
        tier_amount(tiers.INCOME, 12_000)
