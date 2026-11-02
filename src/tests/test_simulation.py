"""蒙特卡洛与安全提取率用例。"""

from __future__ import annotations

import pytest

from simulation import (
    MonteCarloInput,
    WithdrawalInput,
    generate_real_paths,
    return_parameters,
    safe_withdrawal,
    simulate,
)
from simulation.statistics import percentile


def make_mc(**overrides: object) -> MonteCarloInput:
    data = {
        "current_savings": 500_000,
        "monthly_contribution": 3_000,
        "years_to_retirement": 10,
        "retirement_years": 20,
        "annual_return_pct": 5,
        "volatility_pct": 0,
        "inflation_pct": 2,
        "annual_retirement_expense": 60_000,
        "monthly_pension": 0,
        "paths": 500,
        "seed": 42,
    }
    data.update(overrides)
    return MonteCarloInput(**data)


def make_withdrawal(**overrides: object) -> WithdrawalInput:
    data = {
        "retirement_savings": 1_000_000,
        "retirement_years": 25,
        "annual_return_pct": 5,
        "volatility_pct": 10,
        "inflation_pct": 2,
        "target_success_rate": 90,
        "paths": 500,
        "seed": 42,
    }
    data.update(overrides)
    return WithdrawalInput(**data)


def test_same_seed_same_result() -> None:
    first = simulate(make_mc())
    second = simulate(make_mc())
    assert first == second


def test_different_seed_changes_result() -> None:
    first = simulate(make_mc(paths=200, volatility_pct=15))
    second = simulate(make_mc(paths=200, volatility_pct=15, seed=7))
    assert first != second


def test_zero_volatility_matches_closed_form() -> None:
    data = make_mc()
    result = simulate(data)
    real = (1 + data.annual_return_pct / 100) / (1 + data.inflation_pct / 100) - 1

    balance = data.current_savings * (1 + real) ** data.years_to_retirement
    balance += data.monthly_contribution * 12 * (
        ((1 + real) ** data.years_to_retirement - 1) / real
    )
    withdrawal = data.annual_retirement_expense - data.monthly_pension * 12
    expected = balance * (1 + real) ** data.retirement_years
    expected -= withdrawal * (((1 + real) ** data.retirement_years - 1) / real)

    assert result.terminal_balance_percentiles["p50"] == pytest.approx(expected, rel=1e-9)
    assert result.success_rate == 100
    assert result.failed_paths == 0
    assert result.depletion_year_percentiles == {}


def test_zero_volatility_zero_rate_matches_linear_projection() -> None:
    data = make_mc(
        annual_return_pct=2,
        inflation_pct=2,
        years_to_retirement=10,
        retirement_years=19,
    )
    result = simulate(data)
    balance = data.current_savings + data.monthly_contribution * 12 * data.years_to_retirement
    expected = balance - (data.annual_retirement_expense - data.monthly_pension * 12) * (
        data.retirement_years
    )
    assert result.terminal_balance_percentiles["p50"] == pytest.approx(expected)


def test_success_rate_and_failed_paths_are_consistent() -> None:
    result = simulate(make_mc(volatility_pct=20, paths=500))
    assert 0 <= result.success_rate <= 100
    assert result.failed_paths == pytest.approx(500 * (100 - result.success_rate) / 100)
    assert (result.failed_paths == 0) == (result.depletion_year_percentiles == {})


def test_higher_retirement_expense_never_increases_success() -> None:
    low = simulate(make_mc(volatility_pct=15, annual_retirement_expense=50_000))
    high = simulate(make_mc(volatility_pct=15, annual_retirement_expense=90_000))
    assert high.success_rate <= low.success_rate


def test_pension_covering_expense_is_always_success() -> None:
    result = simulate(
        make_mc(
            volatility_pct=20,
            annual_retirement_expense=36_000,
            monthly_pension=3_000,
        )
    )
    assert result.success_rate == 100


def test_balance_percentiles_cover_every_year_and_are_ordered() -> None:
    data = make_mc(volatility_pct=15)
    result = simulate(data)
    total = data.years_to_retirement + data.retirement_years
    assert [point.year for point in result.balance_percentiles] == list(range(total + 1))
    for point in result.balance_percentiles:
        assert point.p10 <= point.p50 <= point.p90


def test_terminal_percentiles_are_ordered() -> None:
    result = simulate(make_mc(volatility_pct=15))
    keys = ["p10", "p25", "p50", "p75", "p90"]
    values = [result.terminal_balance_percentiles[key] for key in keys]
    assert values == sorted(values)


def test_depletion_year_percentiles_are_ordered() -> None:
    result = simulate(
        make_mc(
            volatility_pct=20,
            annual_retirement_expense=120_000,
            retirement_years=30,
        )
    )
    assert result.depletion_year_percentiles
    values = list(result.depletion_year_percentiles.values())
    assert values == sorted(values)
    assert all(1 <= value <= 30 for value in values)


def test_return_parameters_zero_volatility() -> None:
    mean_gross, log_sigma = return_parameters(5, 0)
    assert mean_gross == 1.05
    assert log_sigma == 0


def test_generate_paths_is_reproducible_and_real() -> None:
    first = generate_real_paths(
        seed=1,
        paths=3,
        years=5,
        annual_return_pct=5,
        volatility_pct=10,
        inflation_pct=2,
    )
    second = generate_real_paths(
        seed=1,
        paths=3,
        years=5,
        annual_return_pct=5,
        volatility_pct=10,
        inflation_pct=2,
    )
    assert first == second
    assert all(value > 0 for path in first for value in path)
    # 实际毛收益率的样本均值应接近 (1.05 / 1.02)。
    values = [value for path in first for value in path]
    assert sum(values) / len(values) == pytest.approx(1.05 / 1.02, rel=0.15)


def test_percentile_interpolates() -> None:
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([1, 2, 3, 4], 0) == 1
    assert percentile([1, 2, 3, 4], 1) == 4
    assert percentile([7], 0.9) == 7
    with pytest.raises(ValueError):
        percentile([], 0.5)
    with pytest.raises(ValueError):
        percentile([1, 2], 1.5)


def test_safe_withdrawal_is_positive_and_meets_target() -> None:
    data = make_withdrawal()
    result = safe_withdrawal(data)
    assert 0 < result.safe_withdrawal_rate_pct < 100
    assert result.success_rate_at_rate >= data.target_success_rate
    assert result.annual_withdrawal_real == pytest.approx(
        data.retirement_savings * result.safe_withdrawal_rate_pct / 100
    )
    assert result.monthly_withdrawal_real == pytest.approx(
        result.annual_withdrawal_real / 12
    )


def test_safe_withdrawal_is_reproducible() -> None:
    assert safe_withdrawal(make_withdrawal()) == safe_withdrawal(make_withdrawal())


def test_higher_target_success_rate_requires_lower_withdrawal() -> None:
    low = safe_withdrawal(make_withdrawal(target_success_rate=80))
    high = safe_withdrawal(make_withdrawal(target_success_rate=95))
    assert low.safe_withdrawal_rate_pct >= high.safe_withdrawal_rate_pct


def test_safe_withdrawal_with_zero_savings() -> None:
    result = safe_withdrawal(make_withdrawal(retirement_savings=0))
    assert result.safe_withdrawal_rate_pct == 0
    assert result.annual_withdrawal_real == 0
    assert result.success_rate_at_rate == 100


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("paths", 99),
        ("paths", 20_001),
        ("years_to_retirement", 0),
        ("years_to_retirement", 51),
        ("retirement_years", 0),
        ("retirement_years", 61),
        ("volatility_pct", -1),
        ("volatility_pct", 41),
        ("annual_return_pct", -6),
        ("annual_return_pct", 16),
        ("inflation_pct", 11),
        ("seed", -1),
        ("seed", 2**31),
    ],
)
def test_monte_carlo_rejects_invalid_inputs(field: str, value: object) -> None:
    kwargs = {
        "current_savings": 500_000,
        "monthly_contribution": 3_000,
        "years_to_retirement": 10,
        "retirement_years": 20,
        "annual_return_pct": 5,
        "volatility_pct": 10,
        "inflation_pct": 2,
        "annual_retirement_expense": 60_000,
        "monthly_pension": 0,
        "paths": 500,
        "seed": 42,
    }
    kwargs[field] = value
    with pytest.raises(ValueError):
        MonteCarloInput(**kwargs)


def test_withdrawal_rejects_invalid_target() -> None:
    with pytest.raises(ValueError):
        make_withdrawal(target_success_rate=49)
    with pytest.raises(ValueError):
        make_withdrawal(target_success_rate=100)
