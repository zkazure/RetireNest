"""基础测算引擎的契约对拍与边界用例。"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from plan import PlanInput, build_explanation, build_scenarios, calculate, validate

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "frontend" / "contracts"
REQUEST = json.loads((CONTRACTS / "plan-request.example.json").read_text(encoding="utf-8"))
RESPONSE = json.loads((CONTRACTS / "plan-response.example.json").read_text(encoding="utf-8"))


def example_input() -> PlanInput:
    values = REQUEST["values"]
    return PlanInput(
        city=values["city"],
        age=values["age"],
        retirement_age=values["retire_age"],
        life_expectancy=values["life_expectancy"],
        monthly_income=values["monthly_income"],
        monthly_expense=values["monthly_expense"],
        assets=values["assets"],
        debt=values["debt"],
        retirement_expense=values["retirement_expense"],
        monthly_pension=values["monthly_pension"],
        nominal_return=values["nominal_return"],
        inflation=values["inflation"],
    )


def test_example_matches_contract_response() -> None:
    result = calculate(example_input())
    expected = RESPONSE["result"]

    assert result.years_to_retirement == expected["yearsToRetirement"]
    assert result.retirement_years == expected["retirementYears"]
    assert result.real_return == pytest.approx(expected["realReturn"], rel=1e-12)
    assert result.monthly_surplus == pytest.approx(expected["monthlySurplus"])
    assert result.target == pytest.approx(expected["target"], rel=1e-12)
    assert result.projected == pytest.approx(expected["projected"], rel=1e-12)
    assert result.gap == pytest.approx(expected["gap"], rel=1e-12)
    assert result.coverage == pytest.approx(expected["coverage"], rel=1e-12)
    assert result.required_monthly_saving == pytest.approx(
        expected["requiredMonthlySaving"], rel=1e-12
    )
    assert result.depleted_age == expected["depletedAge"]


def test_points_are_contiguous_from_age_to_life_expectancy() -> None:
    plan_input = example_input()
    result = calculate(plan_input)
    expected = RESPONSE["result"]["points"]

    assert len(result.points) == plan_input.life_expectancy - plan_input.age + 1
    assert [point.age for point in result.points] == [point["age"] for point in expected]
    for point, expected_point in zip(result.points, expected, strict=True):
        assert point.assets == pytest.approx(expected_point["assets"], rel=1e-12)


def test_scenarios_are_conservative_baseline_and_optimistic() -> None:
    plan_input = example_input()
    result = calculate(plan_input)
    scenarios = build_scenarios(plan_input)

    assert [scenario.id for scenario in scenarios] == [
        "conservative",
        "baseline",
        "optimistic",
    ]
    assert [scenario.nominal_return for scenario in scenarios] == [2.0, 3.0, 4.0]
    assert scenarios[1].target == pytest.approx(result.target)
    assert scenarios[1].projected == pytest.approx(result.projected)
    assert scenarios[1].gap == pytest.approx(result.gap)
    assert all(scenario.gap >= 0 for scenario in scenarios)
    assert scenarios[2].gap == 0


def test_scenario_rates_are_clamped_to_supported_range() -> None:
    plan_input = replace(example_input(), nominal_return=-5.0)
    scenarios = build_scenarios(plan_input)
    assert [scenario.nominal_return for scenario in scenarios] == [-5.0, -5.0, -4.0]

    plan_input = replace(example_input(), nominal_return=15.0)
    scenarios = build_scenarios(plan_input)
    assert [scenario.nominal_return for scenario in scenarios] == [14.0, 15.0, 15.0]


def test_validation_collects_field_errors() -> None:
    invalid = replace(example_input(), age=80, retirement_age=70, life_expectancy=60)
    errors = validate(invalid)
    fields = {error.field for error in errors}
    assert {"retire_age", "life_expectancy"} <= fields

    assert validate(replace(example_input(), monthly_expense=0))[0].field == "monthly_expense"
    assert validate(replace(example_input(), inflation=11))[0].field == "inflation"
    assert validate(replace(example_input(), nominal_return=16))[0].field == "nominal_return"
    assert validate(replace(example_input(), city=""))[0].field == "city"


def test_invalid_input_is_rejected_by_calculate() -> None:
    with pytest.raises(ValueError):
        calculate(replace(example_input(), age=80, retirement_age=70))


def test_zero_target_has_full_coverage() -> None:
    plan_input = replace(example_input(), retirement_expense=0, monthly_pension=0)
    result = calculate(plan_input)
    assert result.target == 0
    assert result.coverage == 100


def test_explanation_mentions_gap_or_coverage() -> None:
    plan_input = example_input()
    result = calculate(plan_input)
    explanation = build_explanation(plan_input, result)
    assert "缺口" in explanation

    covered = replace(plan_input, assets=5_000_000)
    covered_result = calculate(covered)
    assert "覆盖" in build_explanation(covered, covered_result)
