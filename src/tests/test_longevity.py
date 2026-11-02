"""Gompertz 寿命模型用例。"""

from __future__ import annotations

import itertools

import pytest

from longevity import (
    LongevityInput,
    calibrate_m,
    conditional_survival,
    estimate,
    expected_life,
    quantile_age,
    survival,
)
from longevity.params import BASE_LIFE_EXPECTANCY, DISPERSION_B, HEALTH_SHIFT


def test_survival_starts_at_one_and_is_non_increasing() -> None:
    m = calibrate_m(78, DISPERSION_B)
    values = [survival(age, m, DISPERSION_B) for age in range(0, 121, 5)]
    assert values[0] == pytest.approx(1)
    assert all(left >= right for left, right in itertools.pairwise(values))
    assert values[-1] < 0.01


@pytest.mark.parametrize(("sex", "health"), [("男", "较差"), ("男", "一般"), ("女", "良好")])
def test_calibration_reproduces_target_life_expectancy(sex: str, health: str) -> None:
    target = BASE_LIFE_EXPECTANCY[sex] + HEALTH_SHIFT[health]
    m = calibrate_m(target, DISPERSION_B)
    assert expected_life(m, DISPERSION_B) == pytest.approx(target, abs=0.01)


def test_percentiles_are_ordered_and_stay_within_range() -> None:
    result = estimate(LongevityInput(current_age=30, sex="男", health="一般"))
    ages = [
        result.p10_age_at_death,
        result.p25_age_at_death,
        result.median_age_at_death,
        result.p75_age_at_death,
        result.p90_age_at_death,
    ]
    assert ages == sorted(ages)
    assert result.p10_age_at_death >= 30
    assert result.p90_age_at_death <= 120


def test_remaining_years_follow_median() -> None:
    result = estimate(LongevityInput(current_age=40, sex="女", health="良好"))
    assert result.median_remaining_years == pytest.approx(
        result.median_age_at_death - 40
    )


def test_women_live_longer_than_men() -> None:
    man = estimate(LongevityInput(current_age=30, sex="男", health="一般"))
    woman = estimate(LongevityInput(current_age=30, sex="女", health="一般"))
    assert woman.median_age_at_death > man.median_age_at_death


def test_better_health_lives_longer() -> None:
    fair = estimate(LongevityInput(current_age=30, sex="男", health="较差"))
    normal = estimate(LongevityInput(current_age=30, sex="男", health="一般"))
    good = estimate(LongevityInput(current_age=30, sex="男", health="良好"))
    assert fair.median_age_at_death < normal.median_age_at_death < good.median_age_at_death


def test_life_expectancy_used_reflects_sex_and_health() -> None:
    result = estimate(LongevityInput(current_age=30, sex="男", health="一般"))
    assert result.life_expectancy_at_birth_used == pytest.approx(BASE_LIFE_EXPECTANCY["男"])

    improved = estimate(LongevityInput(current_age=30, sex="男", health="良好"))
    assert improved.life_expectancy_at_birth_used == pytest.approx(
        BASE_LIFE_EXPECTANCY["男"] + HEALTH_SHIFT["良好"]
    )


def test_survival_probabilities_are_monotonic_in_target_age() -> None:
    result = estimate(LongevityInput(current_age=30, sex="女", health="一般"))
    assert 0 <= result.probability_to_95 <= result.probability_to_90
    assert result.probability_to_90 <= result.probability_to_85 <= 1


def test_probability_is_one_when_already_past_target() -> None:
    result = estimate(LongevityInput(current_age=96, sex="男", health="一般"))
    assert result.probability_to_85 == 1
    assert result.probability_to_90 == 1
    assert result.probability_to_95 == 1


def test_conditional_survival_uses_current_age() -> None:
    m = calibrate_m(78, DISPERSION_B)
    older = conditional_survival(90, 80, m, DISPERSION_B)
    younger = conditional_survival(90, 30, m, DISPERSION_B)
    assert 0 < younger < older < 1


def test_quantile_age_requires_fraction_between_zero_and_one() -> None:
    m = calibrate_m(78, DISPERSION_B)
    assert quantile_age(30, m, DISPERSION_B, 0.5) > 30
    with pytest.raises(ValueError):
        quantile_age(30, m, DISPERSION_B, 0)
    with pytest.raises(ValueError):
        quantile_age(30, m, DISPERSION_B, 1)


@pytest.mark.parametrize(
    ("age", "sex", "health"),
    [
        (17, "男", "一般"),
        (101, "男", "一般"),
        (30, "其他", "一般"),
        (30, "男", "未知"),
    ],
)
def test_invalid_inputs_are_rejected(age: int, sex: str, health: str) -> None:
    with pytest.raises(ValueError):
        LongevityInput(current_age=age, sex=sex, health=health)
