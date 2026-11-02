"""医疗三态：无病无灾、小病小灾、大病大灾。

结构已经定稿，概率与成本是 `[待转录]` 的临时值，等重疾表 CI4 拿到后整表替换：
替换时只改本文件，`lifecycle` 不需要动。口径见 docs/data-sources.md §1。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

HEALTHY, MINOR, MAJOR = "healthy", "minor", "major"
STATES = (HEALTHY, MINOR, MAJOR)

BASELINE_ANNUAL = 1_200.0
"""[假设] 每年门诊、日常用药与体检。"""

MINOR_EXTRA = 12_000.0
"""[待核] 小病小灾的额外支出：2024 年次均住院费用 9870 元，上浮到 12000 含自费与陪护。"""

MAJOR_EXTRA = 150_000.0
"""[假设] 单次大病总成本：治疗、护理与收入损失，含自费药与康复。"""

SEX_FACTORS = {"男": 1.0, "女": 0.7}
"""[待转录] 女性重疾发生率整体低于男性，用 0.7 近似，拿到 CI4 后按表替换。"""

AGE_BANDS = (
    (18, 39, 0.06, 0.0015),
    (40, 49, 0.10, 0.0040),
    (50, 59, 0.16, 0.0080),
    (60, 69, 0.26, 0.0140),
    (70, 79, 0.36, 0.0220),
    (80, 120, 0.45, 0.0280),
)
"""(起, 止, 小病概率, 大病概率)；小病概率对齐年住院率约 22%，大病概率待转录。"""


@dataclass(frozen=True, slots=True)
class TriStateProbability:
    healthy: float
    minor: float
    major: float

    def __post_init__(self) -> None:
        total = self.healthy + self.minor + self.major
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"三态概率之和必须为 1，收到 {total:.6f}")


@dataclass(frozen=True, slots=True)
class TriStateCost:
    healthy: float
    minor: float
    major: float


def probabilities(age: int, sex: str) -> TriStateProbability:
    if isinstance(age, bool) or not isinstance(age, int) or not 18 <= age <= 120:
        raise ValueError("年龄需在 18 到 120 岁之间。")
    if sex not in SEX_FACTORS:
        raise ValueError(f"未知性别：{sex!r}")
    for start, end, minor_p, major_p in AGE_BANDS:
        if start <= age <= end:
            break
    factor = SEX_FACTORS[sex]
    minor = minor_p
    major = min(major_p * factor, 1.0 - minor)
    return TriStateProbability(healthy=round(1 - minor - major, 10), minor=minor, major=major)


def costs() -> TriStateCost:
    return TriStateCost(
        healthy=BASELINE_ANNUAL,
        minor=BASELINE_ANNUAL + MINOR_EXTRA,
        major=BASELINE_ANNUAL + MAJOR_EXTRA,
    )


def event_cost(state: str) -> float:
    table = costs()
    if state not in STATES:
        raise ValueError(f"未知医疗状态：{state!r}")
    return getattr(table, state)


def expected_annual(age: int, sex: str) -> float:
    """期望年医疗支出：三态概率乘各自年支出。"""
    p = probabilities(age, sex)
    table = costs()
    value = p.healthy * table.healthy + p.minor * table.minor + p.major * table.major
    if not math.isfinite(value) or value < 0:
        raise ValueError("医疗支出必须是非负有限数。")
    return round(value, 2)
