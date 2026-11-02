"""寿命估计的输入输出。

年龄单位为周岁；概率是 0–1 的比例，不是百分数。
"""

from __future__ import annotations

from dataclasses import dataclass

from longevity.params import BASE_LIFE_EXPECTANCY, HEALTH_SHIFT

MIN_AGE = 18
MAX_AGE = 100


@dataclass(frozen=True, slots=True)
class LongevityInput:
    """当前年龄、性别与健康档位。"""

    current_age: int
    sex: str
    health: str = "一般"

    def __post_init__(self) -> None:
        if not MIN_AGE <= self.current_age <= MAX_AGE:
            raise ValueError(f"当前年龄需在 {MIN_AGE} 到 {MAX_AGE} 岁之间。")
        if self.sex not in BASE_LIFE_EXPECTANCY:
            raise ValueError(f"未知性别：{self.sex}")
        if self.health not in HEALTH_SHIFT:
            raise ValueError(f"未知健康档位：{self.health}")


@dataclass(frozen=True, slots=True)
class LongevityResult:
    """条件于当前年龄的死亡年龄分位与存活概率。"""

    median_age_at_death: float
    p10_age_at_death: float
    p25_age_at_death: float
    p75_age_at_death: float
    p90_age_at_death: float
    probability_to_85: float
    probability_to_90: float
    probability_to_95: float
    median_remaining_years: float
    life_expectancy_at_birth_used: float
