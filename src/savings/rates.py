"""复利与年金原语。

实际收益率沿用 `plan.engine` 的口径：

    实际年回报率 = (1 + 名义年回报率) / (1 + 通胀率) - 1

年金系数默认期末投入；`r≈0` 时退化为期数，避免除零。
"""

from __future__ import annotations

import math

from savings.models import TIMING_BEGIN, TIMING_END

ZERO_RATE = 1e-9
"""低于这个阈值视为零收益率，与 `plan.engine.py` 的判断保持一致。"""


def real_rate(nominal_pct: float, inflation_pct: float) -> float:
    """把名义年回报率与通胀率折算成实际年回报率。"""
    return (1 + nominal_pct / 100) / (1 + inflation_pct / 100) - 1


def period_rate(annual_rate: float, periods_per_year: int) -> float:
    """把实际年收益率折算成每期收益率，按期复利。"""
    if periods_per_year <= 0:
        raise ValueError("每年期数必须大于 0。")
    if periods_per_year == 1:
        return annual_rate
    return math.expm1(math.log1p(annual_rate) / periods_per_year)


def annuity_factor(rate: float, periods: int, timing: str = TIMING_END) -> float:
    """普通年金终值系数；`timing="begin"` 时为期初年金。"""
    if periods < 0:
        raise ValueError("期数不能为负。")
    if periods == 0:
        return 0.0
    if abs(rate) < ZERO_RATE:
        factor = float(periods)
    else:
        factor = math.expm1(periods * math.log1p(rate)) / rate
    if timing == TIMING_BEGIN:
        factor *= 1 + rate
    elif timing != TIMING_END:
        raise ValueError(f"未知投入时点：{timing}")
    return factor


def future_value(
    present: float,
    rate: float,
    periods: int,
    contribution: float,
    timing: str = TIMING_END,
) -> float:
    """一笔现值加每期投入的未来值。"""
    return present * (1 + rate) ** periods + contribution * annuity_factor(rate, periods, timing)
