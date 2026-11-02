"""Gompertz 生存模型：校准、条件生存与死亡年龄分位。

生存函数（从出生起算）：

    S(x) = exp(-exp((x - m) / b) + exp(-m / b))

`m` 是死亡力曲线的位置参数，`b` 是离散参数。给定出生时预期寿命后，
用数值积分与二分校准 `m`，再按当前年龄做条件化。
"""

from __future__ import annotations

import math
from functools import lru_cache

from longevity.models import LongevityInput, LongevityResult
from longevity.params import (
    BASE_LIFE_EXPECTANCY,
    DISPERSION_B,
    HEALTH_SHIFT,
)
from longevity.params import MAX_AGE as MAX_OUTPUT_AGE

INTEGRATION_STEP = 0.1
CALIBRATION_STEPS = 60
CALIBRATION_LOW = 20.0
CALIBRATION_HIGH = 140.0


def survival(age: float, m: float, b: float) -> float:
    """从出生到 `age` 岁的存活概率。"""
    if age < 0:
        raise ValueError("年龄不能为负。")
    if b <= 0:
        raise ValueError("Gompertz 离散参数必须大于 0。")
    return math.exp(-math.exp((age - m) / b) + math.exp(-m / b))


def expected_life(m: float, b: float) -> float:
    """出生时预期寿命，用梯形积分近似。"""
    steps = int(MAX_OUTPUT_AGE / INTEGRATION_STEP)
    values = [survival(index * INTEGRATION_STEP, m, b) for index in range(steps + 1)]
    middle = math.fsum(values[1:-1])
    return (values[0] / 2 + middle + values[-1] / 2) * INTEGRATION_STEP


@lru_cache(maxsize=256)
def _calibrate(target_life_expectancy: float, b: float) -> float:
    low, high = CALIBRATION_LOW, CALIBRATION_HIGH
    for _ in range(CALIBRATION_STEPS):
        mid = (low + high) / 2
        if expected_life(mid, b) < target_life_expectancy:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def calibrate_m(target_life_expectancy: float, b: float = DISPERSION_B) -> float:
    """求使出生时预期寿命等于目标的 `m`。"""
    if not 0 < target_life_expectancy < MAX_OUTPUT_AGE:
        raise ValueError("目标预期寿命需在 0 到 120 年之间。")
    if b <= 0:
        raise ValueError("Gompertz 离散参数必须大于 0。")
    return _calibrate(round(target_life_expectancy, 9), b)


def conditional_survival(
    target_age: float,
    current_age: float,
    m: float,
    b: float,
) -> float:
    """已知活到 `current_age`，再活到 `target_age` 的概率。"""
    if target_age <= current_age:
        return 1.0
    return min(1.0, survival(target_age, m, b) / survival(current_age, m, b))


def quantile_age(
    current_age: float,
    m: float,
    b: float,
    fraction: float,
) -> float:
    """条件死亡年龄的 `fraction` 分位。"""
    if not 0 < fraction < 1:
        raise ValueError("分位点需在 0 到 1 之间。")
    s_current = survival(current_age, m, b)
    target = (1 - fraction) * s_current
    if target <= 0:
        return MAX_OUTPUT_AGE
    age = m + b * math.log(-math.log(target))
    return min(max(age, current_age), MAX_OUTPUT_AGE)


def estimate(data: LongevityInput) -> LongevityResult:
    """按性别、健康档位校准，输出条件于当前年龄的结果。"""
    b = DISPERSION_B
    target_life_expectancy = BASE_LIFE_EXPECTANCY[data.sex] + HEALTH_SHIFT[data.health]
    m = calibrate_m(target_life_expectancy, b)
    median = quantile_age(data.current_age, m, b, 0.5)
    return LongevityResult(
        median_age_at_death=median,
        p10_age_at_death=quantile_age(data.current_age, m, b, 0.1),
        p25_age_at_death=quantile_age(data.current_age, m, b, 0.25),
        p75_age_at_death=quantile_age(data.current_age, m, b, 0.75),
        p90_age_at_death=quantile_age(data.current_age, m, b, 0.9),
        probability_to_85=conditional_survival(85, data.current_age, m, b),
        probability_to_90=conditional_survival(90, data.current_age, m, b),
        probability_to_95=conditional_survival(95, data.current_age, m, b),
        median_remaining_years=median - data.current_age,
        life_expectancy_at_birth_used=target_life_expectancy,
    )
