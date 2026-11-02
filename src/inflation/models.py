"""名义金额与实际购买力换算的数据结构。

金额单位为元；通胀率用百分数；年限为整数。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

NOMINAL_TO_REAL = "nominal_to_real"
REAL_TO_NOMINAL = "real_to_nominal"

MAX_AMOUNT = 1_000_000_000.0
MIN_INFLATION = 0.0
MAX_INFLATION = 10.0
MAX_YEARS = 60


@dataclass(frozen=True, slots=True)
class InflationInput:
    """一次换算的方向、金额、通胀率与年限。"""

    amount: float
    annual_inflation_pct: float
    years: int
    direction: str = NOMINAL_TO_REAL

    def __post_init__(self) -> None:
        if not math.isfinite(self.amount) or not 0 <= self.amount <= MAX_AMOUNT:
            raise ValueError(f"金额需在 0 到 {MAX_AMOUNT:,.0f} 元之间。")
        if (
            not math.isfinite(self.annual_inflation_pct)
            or not MIN_INFLATION <= self.annual_inflation_pct <= MAX_INFLATION
        ):
            raise ValueError(f"年通胀率需在 {MIN_INFLATION}% 到 {MAX_INFLATION}% 之间。")
        if not 0 <= self.years <= MAX_YEARS:
            raise ValueError(f"年限需在 0 到 {MAX_YEARS} 年之间。")
        if self.direction not in (NOMINAL_TO_REAL, REAL_TO_NOMINAL):
            raise ValueError(f"未知换算方向：{self.direction}")


@dataclass(frozen=True, slots=True)
class InflationResult:
    """换算结果；`cumulative_factor` 是名义金额与实际金额的比值。"""

    converted_amount: float
    cumulative_factor: float
    annual_inflation_pct: float
