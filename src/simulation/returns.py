"""年度实际收益率的随机路径。

模型：名义毛收益率取对数正态，均值为 `1 + 名义年回报率`，标准差为输入波动率；
再用确定性通胀折算成实际毛收益率。于是实际收益率的均值正好等于
`(1 + 名义) / (1 + 通胀) - 1`，但通胀本身不做随机化——通胀不确定性应体现在
更高的波动率输入里。
"""

from __future__ import annotations

import math
import random


def return_parameters(nominal_pct: float, volatility_pct: float) -> tuple[float, float]:
    """返回 (名义毛收益率均值, 对数标准差)；波动率为 0 时标准差为 0。"""
    mean_gross = 1 + nominal_pct / 100
    sigma = volatility_pct / 100
    if sigma <= 0:
        return mean_gross, 0.0
    log_variance = math.log1p((sigma / mean_gross) ** 2)
    return mean_gross, math.sqrt(log_variance)


def sample_real_gross(
    rng: random.Random,
    mean_gross: float,
    log_sigma: float,
    inflation_pct: float,
) -> float:
    """抽一条实际毛收益率；波动率为 0 时退化为常数。"""
    if log_sigma <= 0:
        nominal_gross = mean_gross
    else:
        shock = rng.gauss(0.0, 1.0)
        nominal_gross = mean_gross * math.exp(log_sigma * shock - log_sigma**2 / 2)
    return nominal_gross / (1 + inflation_pct / 100)


def generate_real_paths(
    *,
    seed: int,
    paths: int,
    years: int,
    annual_return_pct: float,
    volatility_pct: float,
    inflation_pct: float,
) -> list[list[float]]:
    """生成 `paths` 条长度为 `years` 的实际毛收益率路径。

    同一个 seed、同一组参数必然得到同一组路径；调用方因此可以把随机模拟
    标成 deterministic。
    """
    mean_gross, log_sigma = return_parameters(annual_return_pct, volatility_pct)
    rng = random.Random(seed)
    return [
        [sample_real_gross(rng, mean_gross, log_sigma, inflation_pct) for _ in range(years)]
        for _ in range(paths)
    ]
