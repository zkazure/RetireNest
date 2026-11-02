"""储蓄增长与目标倒推的纯函数用例。"""

from __future__ import annotations

import math

import pytest

from savings import (
    SavingsGoalInput,
    SavingsProjectInput,
    annuity_factor,
    period_rate,
    project,
    real_rate,
    required_contribution,
)


def test_real_rate_uses_geometric_conversion() -> None:
    assert real_rate(5, 2) == pytest.approx((1.05 / 1.02) - 1)
    assert real_rate(2, 2) == 0
    assert real_rate(0, 3) == pytest.approx(-3 / 103)


def test_annuity_factor_zero_rate_is_periods() -> None:
    assert annuity_factor(0, 10) == 10
    assert annuity_factor(0, 10, "begin") == 10


def test_annuity_factor_begin_multiplies_by_one_plus_rate() -> None:
    end = annuity_factor(0.05, 10, "end")
    begin = annuity_factor(0.05, 10, "begin")
    assert begin == pytest.approx(end * 1.05)


def test_period_rate_compounds_back_to_annual_rate() -> None:
    monthly = period_rate(0.06, 12)
    assert (1 + monthly) ** 12 == pytest.approx(1.06, rel=1e-12)
    assert period_rate(0.06, 1) == 0.06


def test_project_zero_real_return_has_no_growth() -> None:
    result = project(
        SavingsProjectInput(
            current_savings=100_000,
            monthly_contribution=1_000,
            annual_return_pct=2,
            inflation_pct=2,
            years=10,
        )
    )
    assert result.future_balance_real == pytest.approx(220_000)
    assert result.total_contributions_real == pytest.approx(120_000)
    assert result.total_invested_real == pytest.approx(220_000)
    assert result.growth_real == pytest.approx(0)
    assert result.future_balance_nominal == pytest.approx(220_000 * 1.02**10)


def test_project_annual_closed_form() -> None:
    current = 50_000
    monthly = 2_000
    years = 20
    real = real_rate(7, 2)
    expected = current * (1 + real) ** years + monthly * 12 * (
        ((1 + real) ** years - 1) / real
    )
    result = project(
        SavingsProjectInput(
            current_savings=current,
            monthly_contribution=monthly,
            annual_return_pct=7,
            inflation_pct=2,
            years=years,
        )
    )
    assert result.future_balance_real == pytest.approx(expected, rel=1e-12)
    assert result.real_return_pct == pytest.approx(real * 100)


def test_project_monthly_lump_sum_matches_annual() -> None:
    annual = project(
        SavingsProjectInput(
            current_savings=100_000,
            monthly_contribution=0,
            annual_return_pct=6,
            inflation_pct=2,
            years=10,
        )
    )
    monthly = project(
        SavingsProjectInput(
            current_savings=100_000,
            monthly_contribution=0,
            annual_return_pct=6,
            inflation_pct=2,
            years=10,
            compounding="monthly",
        )
    )
    assert monthly.future_balance_real == pytest.approx(annual.future_balance_real, rel=1e-9)


def test_project_monthly_contributions_earn_more_than_annual() -> None:
    annual = project(
        SavingsProjectInput(
            current_savings=100_000,
            monthly_contribution=2_000,
            annual_return_pct=6,
            inflation_pct=2,
            years=10,
        )
    )
    monthly = project(
        SavingsProjectInput(
            current_savings=100_000,
            monthly_contribution=2_000,
            annual_return_pct=6,
            inflation_pct=2,
            years=10,
            compounding="monthly",
        )
    )
    assert monthly.future_balance_real > annual.future_balance_real


def test_project_begin_timing_is_larger_than_end() -> None:
    end = project(
        SavingsProjectInput(
            current_savings=0,
            monthly_contribution=2_000,
            annual_return_pct=5,
            inflation_pct=2,
            years=10,
        )
    )
    begin = project(
        SavingsProjectInput(
            current_savings=0,
            monthly_contribution=2_000,
            annual_return_pct=5,
            inflation_pct=2,
            years=10,
            timing="begin",
        )
    )
    assert begin.future_balance_real > end.future_balance_real


def test_goal_required_contribution_reaches_target() -> None:
    goal = required_contribution(
        SavingsGoalInput(
            target_amount=1_000_000,
            current_savings=100_000,
            annual_return_pct=6,
            inflation_pct=2,
            years=20,
        )
    )
    assert goal.shortfall_real > 0

    projection = project(
        SavingsProjectInput(
            current_savings=100_000,
            monthly_contribution=goal.required_monthly_contribution_real,
            annual_return_pct=6,
            inflation_pct=2,
            years=20,
        )
    )
    assert projection.future_balance_real == pytest.approx(1_000_000, rel=1e-9)
    assert goal.required_annual_contribution_real == pytest.approx(
        goal.required_monthly_contribution_real * 12
    )


def test_goal_monthly_compounding_reaches_target() -> None:
    goal = required_contribution(
        SavingsGoalInput(
            target_amount=800_000,
            current_savings=50_000,
            annual_return_pct=6,
            inflation_pct=2,
            years=15,
            compounding="monthly",
        )
    )
    projection = project(
        SavingsProjectInput(
            current_savings=50_000,
            monthly_contribution=goal.required_monthly_contribution_real,
            annual_return_pct=6,
            inflation_pct=2,
            years=15,
            compounding="monthly",
        )
    )
    assert projection.future_balance_real == pytest.approx(800_000, rel=1e-9)


def test_goal_is_zero_when_current_savings_already_cover_target() -> None:
    goal = required_contribution(
        SavingsGoalInput(
            target_amount=100_000,
            current_savings=200_000,
            annual_return_pct=5,
            inflation_pct=2,
            years=10,
        )
    )
    assert goal.required_monthly_contribution_real == 0
    assert goal.required_annual_contribution_real == 0
    assert goal.shortfall_real == 0
    assert goal.projected_without_contribution_real > 100_000


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("annual_return_pct", -6),
        ("annual_return_pct", 16),
        ("inflation_pct", -1),
        ("inflation_pct", 11),
        ("years", 0),
        ("years", 61),
        ("compounding", "daily"),
        ("timing", "middle"),
    ],
)
def test_project_rejects_invalid_assumptions(field: str, value: object) -> None:
    kwargs = {
        "current_savings": 100_000,
        "monthly_contribution": 1_000,
        "annual_return_pct": 5,
        "inflation_pct": 2,
        "years": 10,
    }
    kwargs[field] = value
    with pytest.raises(ValueError):
        SavingsProjectInput(**kwargs)


def test_project_rejects_negative_amounts() -> None:
    with pytest.raises(ValueError):
        SavingsProjectInput(
            current_savings=-1,
            monthly_contribution=1_000,
            annual_return_pct=5,
            inflation_pct=2,
            years=10,
        )
    with pytest.raises(ValueError):
        SavingsProjectInput(
            current_savings=0,
            monthly_contribution=-1,
            annual_return_pct=5,
            inflation_pct=2,
            years=10,
        )


def test_values_are_finite_for_extreme_but_valid_inputs() -> None:
    result = project(
        SavingsProjectInput(
            current_savings=1_000_000_000,
            monthly_contribution=1_000_000_000,
            annual_return_pct=15,
            inflation_pct=0,
            years=60,
        )
    )
    assert math.isfinite(result.future_balance_real)
    assert math.isfinite(result.future_balance_nominal)
