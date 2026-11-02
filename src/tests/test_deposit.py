"""活期收益计算的测试：口径、精度与边界。"""

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest

from deposit import DEFAULT_ANNUAL_RATE, DemandDeposit, DepositError, calculate


def make(
    principal: object = "100000",
    start: date = date(2026, 1, 1),
    end: date = date(2027, 1, 1),
    rate: object = None,
) -> DemandDeposit:
    return DemandDeposit(principal=principal, start_date=start, end_date=end, annual_rate=rate)


def test_readme_example():
    result = calculate(make())
    assert result.days == 365
    assert result.interest == Decimal("50.69")
    assert result.total == Decimal("100050.69")


def test_days_count_start_not_end():
    result = calculate(make(end=date(2026, 1, 2)))
    assert result.days == 1
    assert result.interest == Decimal("0.14")


def test_leap_year_uses_actual_days():
    result = calculate(make(start=date(2024, 1, 1), end=date(2025, 1, 1)))
    assert result.days == 366
    assert result.interest == Decimal("50.83")


def test_zero_rate_yields_zero():
    result = calculate(make(rate="0"))
    assert result.interest == Decimal("0.00")
    assert result.total == Decimal("100000.00")


def test_default_rate_is_used_when_omitted():
    omitted = calculate(make())
    explicit = calculate(make(rate="0.0005"))
    assert omitted.annual_rate == DEFAULT_ANNUAL_RATE
    assert omitted == explicit


def test_half_cent_rounds_up():
    # 3600 元、0.05%、1 天：利息恰好 0.005，四舍五入到 0.01
    result = calculate(make(principal="3600", end=date(2026, 1, 2)))
    assert result.interest == Decimal("0.01")


def test_tiny_principal_rounds_to_zero():
    result = calculate(make(principal="0.01"))
    assert result.interest == Decimal("0.00")


def test_accepts_int_principal_and_str_rate():
    result = calculate(make(principal=100000, rate="0.0005"))
    assert result.principal == Decimal(100000)
    assert result.interest == Decimal("50.69")


def test_daily_rate_is_display_only():
    result = calculate(make())
    assert result.daily_rate == Decimal("0.0000013889")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"principal": "0"}, "本金必须大于 0"),
        ({"principal": "-1"}, "本金必须大于 0"),
        ({"principal": "1.005"}, "最多保留两位小数"),
        ({"rate": "-0.0001"}, "年利率不能为负"),
        ({"end": date(2026, 1, 1)}, "必须晚于起始日期"),
        ({"end": date(2025, 12, 31)}, "必须晚于起始日期"),
        ({"principal": 100000.0}, "float 会带出浮点误差"),
        ({"rate": 0.0005}, "float 会带出浮点误差"),
        ({"principal": "abc"}, "不是合法数字"),
        ({"principal": True}, "不接受布尔值"),
    ],
)
def test_rejects_invalid_input(overrides, message):
    with pytest.raises(DepositError, match=message):
        make(**overrides)


def test_input_is_immutable():
    deposit = make()
    with pytest.raises(FrozenInstanceError):
        deposit.principal = Decimal(1)
