"""通胀换算：名义金额与实际购买力互转。

    名义转实际：实际 = 名义 / (1 + 通胀率)^年数
    实际转名义：名义 = 实际 × (1 + 通胀率)^年数

`savings.*` 与 `simulation.*` 已经内含通胀，不要把这里的结果再套一次。
"""

from __future__ import annotations

from inflation.models import (
    NOMINAL_TO_REAL,
    InflationInput,
    InflationResult,
)


def convert(data: InflationInput) -> InflationResult:
    """按年复利折算购买力；方向只决定乘除，不改变累计系数。"""
    factor = (1 + data.annual_inflation_pct / 100) ** data.years
    if data.direction == NOMINAL_TO_REAL:
        converted = data.amount / factor
    else:
        converted = data.amount * factor
    return InflationResult(
        converted_amount=converted,
        cumulative_factor=factor,
        annual_inflation_pct=data.annual_inflation_pct,
    )
