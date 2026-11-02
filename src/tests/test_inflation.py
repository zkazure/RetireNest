"""通胀换算用例。"""

from __future__ import annotations

import pytest

from inflation import InflationInput, convert


def test_nominal_to_real_discounts_by_inflation() -> None:
    result = convert(InflationInput(amount=100_000, annual_inflation_pct=2, years=10))
    assert result.cumulative_factor == pytest.approx(1.02**10)
    assert result.converted_amount == pytest.approx(100_000 / 1.02**10)
    assert result.annual_inflation_pct == 2


def test_real_to_nominal_inflates_by_inflation() -> None:
    result = convert(
        InflationInput(
            amount=100_000,
            annual_inflation_pct=3,
            years=20,
            direction="real_to_nominal",
        )
    )
    assert result.converted_amount == pytest.approx(100_000 * 1.03**20)


def test_zero_years_is_identity() -> None:
    nominal = convert(InflationInput(amount=12_345, annual_inflation_pct=5, years=0))
    real = convert(
        InflationInput(
            amount=12_345,
            annual_inflation_pct=5,
            years=0,
            direction="real_to_nominal",
        )
    )
    assert nominal.converted_amount == 12_345
    assert real.converted_amount == 12_345
    assert nominal.cumulative_factor == 1


def test_zero_inflation_is_identity() -> None:
    result = convert(InflationInput(amount=50_000, annual_inflation_pct=0, years=30))
    assert result.converted_amount == 50_000
    assert result.cumulative_factor == 1


def test_round_trip_returns_original_amount() -> None:
    nominal = convert(InflationInput(amount=88_888, annual_inflation_pct=2.5, years=25))
    back = convert(
        InflationInput(
            amount=nominal.converted_amount,
            annual_inflation_pct=2.5,
            years=25,
            direction="real_to_nominal",
        )
    )
    assert back.converted_amount == pytest.approx(88_888, rel=1e-12)


@pytest.mark.parametrize(
    ("amount", "inflation", "years", "direction"),
    [
        (-1, 2, 10, "nominal_to_real"),
        (1_000_000_001, 2, 10, "nominal_to_real"),
        (1_000, -1, 10, "nominal_to_real"),
        (1_000, 11, 10, "nominal_to_real"),
        (1_000, 2, -1, "nominal_to_real"),
        (1_000, 2, 61, "nominal_to_real"),
        (1_000, 2, 10, "sideways"),
    ],
)
def test_invalid_inputs_are_rejected(
    amount: float,
    inflation: float,
    years: int,
    direction: str,
) -> None:
    with pytest.raises(ValueError):
        InflationInput(
            amount=amount,
            annual_inflation_pct=inflation,
            years=years,
            direction=direction,
        )
