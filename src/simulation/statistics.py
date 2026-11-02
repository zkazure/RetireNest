"""模拟结果的分位数工具。"""

from __future__ import annotations

import math
from collections.abc import Sequence

RETIREMENT_PERCENTILES = (0.1, 0.25, 0.5, 0.75, 0.9)
DEPLETION_PERCENTILES = (0.1, 0.5, 0.9)


def percentile(values: Sequence[float] | Sequence[int], fraction: float) -> float:
    """线性插值分位数；`fraction` 取 0–1。"""
    if not values:
        raise ValueError("空序列没有分位数。")
    if not 0 <= fraction <= 1:
        raise ValueError("分位点需在 0 到 1 之间。")
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * fraction
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(ordered[lower])
    return float(ordered[lower]) + (float(ordered[upper]) - float(ordered[lower])) * (rank - lower)


def percentile_map(
    values: Sequence[float] | Sequence[int],
    fractions: tuple[float, ...],
) -> dict[str, float]:
    if not values:
        return {}
    return {f"p{int(fraction * 100)}": percentile(values, fraction) for fraction in fractions}
