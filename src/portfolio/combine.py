"""把三档配比合成组合的收益与波动。"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from portfolio.assumptions import ASSET_CLASSES, correlation
from portfolio.errors import PortfolioError


@dataclass(frozen=True, slots=True)
class Allocation:
    high: float = 0.3
    mid: float = 0.5
    low: float = 0.2

    def __post_init__(self) -> None:
        values = {"high": self.high, "mid": self.mid, "low": self.low}
        for key, value in values.items():
            if not math.isfinite(value) or value < 0:
                raise PortfolioError(f"{key} 配比必须是非负有限数，收到 {value!r}")
        total = sum(values.values())
        if abs(total - 1.0) > 1e-9:
            raise PortfolioError(f"配比之和必须为 1，收到 {total:.4f}")

    def weights(self) -> dict[str, float]:
        return {"high": self.high, "mid": self.mid, "low": self.low}


@dataclass(frozen=True, slots=True)
class PortfolioAssumption:
    annual_return_pct: float
    volatility_pct: float


def combine(weights: Mapping[str, float]) -> PortfolioAssumption:
    """组合期望收益按权重加权，波动按协方差矩阵开方。"""
    clean = _validate(weights)
    keys = [key for key, weight in clean.items() if weight > 0]
    mean = sum(clean[key] * ASSET_CLASSES[key].annual_return_pct for key in keys)
    variance = 0.0
    for left in keys:
        for right in keys:
            sigma_left = ASSET_CLASSES[left].volatility_pct
            sigma_right = ASSET_CLASSES[right].volatility_pct
            variance += (
                clean[left]
                * clean[right]
                * sigma_left
                * sigma_right
                * correlation(left, right)
            )
    return PortfolioAssumption(
        annual_return_pct=round(mean, 6),
        volatility_pct=round(math.sqrt(max(variance, 0.0)), 6),
    )


def _validate(weights: Mapping[str, float]) -> dict[str, float]:
    unknown = set(weights) - set(ASSET_CLASSES)
    if unknown:
        raise PortfolioError(f"未知风险档位：{sorted(unknown)}")
    clean: dict[str, float] = {}
    for key in ASSET_CLASSES:
        weight = float(weights.get(key, 0.0))
        if not math.isfinite(weight) or weight < 0:
            raise PortfolioError(f"{key} 配比必须是非负有限数，收到 {weight!r}")
        clean[key] = weight
    total = sum(clean.values())
    if abs(total - 1.0) > 1e-9:
        raise PortfolioError(f"配比之和必须为 1，收到 {total:.4f}")
    return clean
