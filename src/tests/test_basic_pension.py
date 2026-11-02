"""基础养老金与个人账户养老金的测试。"""

from datetime import date
from decimal import Decimal

import pytest

from pension import BasicPensionInput, PensionError, calculate, latest_adjustment


def make_input(**overrides) -> BasicPensionInput:
    params: dict = {
        "birth_date": date(1965, 6, 1),
        "gender": "男",
        "contribution_years": Decimal(30),
        "average_index": Decimal(1),
        "account_balance": Decimal(150000),
        "calculation_base": Decimal(8000),
        "prior_monthly_wage": Decimal(6000),
    }
    params.update(overrides)
    return BasicPensionInput(**params)


def test_known_example():
    result = calculate(make_input())
    assert result.retirement_age_months == 722
    assert result.payout_months == 139
    assert result.basic_pension == Decimal("2400.00")
    assert result.account_pension == Decimal("1079.14")
    assert result.total == Decimal("3479.14")


def test_result_is_traceable():
    result = calculate(make_input())
    assert result.calculation_base == Decimal(8000)
    assert result.average_index == Decimal(1)
    assert result.contribution_years == Decimal(30)


def test_replacement_rate():
    assert calculate(make_input()).replacement_rate == Decimal("0.5799")


def test_replacement_rate_absent_without_wage():
    assert calculate(make_input(prior_monthly_wage=None)).replacement_rate is None


def test_fifty_five_year_old_payout():
    # 女、管理技术，1969-12 出生 → 55 岁，计发月数 170
    result = calculate(make_input(birth_date=date(1969, 12, 1), gender="女", category="管理技术"))
    assert result.retirement_age_months == 660
    assert result.payout_months == 170
    assert result.account_pension == Decimal("882.35")
    assert result.total == Decimal("3282.35")
    assert result.replacement_rate == Decimal("0.5471")


def test_zero_balance_leaves_only_basic_pension():
    result = calculate(make_input(account_balance=Decimal(0)))
    assert result.account_pension == Decimal("0.00")
    assert result.total == result.basic_pension


def test_default_adjustment_comes_from_snapshot():
    assert calculate(make_input()).annual_adjustment == latest_adjustment()


def test_adjustment_can_be_overridden():
    result = calculate(make_input(annual_adjustment=Decimal("0.05")))
    assert result.annual_adjustment == Decimal("0.05")
    assert result.monthly_at(12) == Decimal("3653.10")


def test_monthly_at_zero_equals_total():
    result = calculate(make_input())
    assert result.monthly_at(0) == result.total
    assert result.monthly_at(11) == result.total


def test_monthly_at_compounds_annually():
    result = calculate(make_input())
    assert result.monthly_at(24) == Decimal("3619.70")


def test_monthly_at_rejects_negative():
    with pytest.raises(PensionError, match="月数"):
        calculate(make_input()).monthly_at(-1)


@pytest.mark.parametrize("index", ["0.6", "3.0"])
def test_index_bounds_are_inclusive(index):
    calculate(make_input(average_index=Decimal(index)))


@pytest.mark.parametrize("index", ["0.59", "3.01"])
def test_index_out_of_bounds(index):
    with pytest.raises(PensionError, match="平均缴费指数"):
        make_input(average_index=Decimal(index))


def test_float_is_rejected():
    with pytest.raises(PensionError, match="float"):
        make_input(contribution_years=30.0)


def test_negative_balance_is_rejected():
    with pytest.raises(PensionError, match="不能为负"):
        make_input(account_balance=Decimal(-1))


def test_zero_base_is_rejected():
    with pytest.raises(PensionError, match="大于 0"):
        make_input(calculation_base=Decimal(0))


@pytest.mark.parametrize("years", ["0", "51"])
def test_contribution_years_bounds(years):
    with pytest.raises(PensionError, match="缴费年限"):
        make_input(contribution_years=Decimal(years))


def test_female_needs_category_at_calculate_time():
    with pytest.raises(PensionError, match="岗位类别"):
        calculate(make_input(gender="女", category=None))
