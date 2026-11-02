"""三档资产的长期收益与波动假设。

数值来自 docs/data-sources.md §2：权益取沪深 300 长期价格指数年化 4.91% 加股息
2.5%，波动取 20%（日频 18.6% 与长窗 26.2% 之间取整）；债券取上证国债指数
3.57%、波动 2.1%，因含少量信用债与基金费差，收益上浮到 4.0%、波动 6%；
活期与定期取 1.5% 与 0.5%，对应 2025 年记账利率与六大行挂牌利率。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssetClass:
    key: str
    label: str
    annual_return_pct: float
    volatility_pct: float
    holding: str


ASSET_CLASSES: dict[str, AssetClass] = {
    "high": AssetClass("high", "高风险", 7.4, 20.0, "股票、股票型基金"),
    "mid": AssetClass("mid", "中风险", 4.0, 6.0, "债券基金、混合基金"),
    "low": AssetClass("low", "低风险", 1.5, 0.5, "活期、定期存款"),
}

CORRELATION: Mapping[tuple[str, str], float] = {
    ("high", "mid"): 0.1,
    ("high", "low"): 0.05,
    ("mid", "low"): 0.3,
}
"""[假设] 相关系数：股债近十年月度相关在 -0.1 到 0.2 之间，取 0.1 作中枢。"""


def correlation(left: str, right: str) -> float:
    if left == right:
        return 1.0
    return CORRELATION.get((left, right), CORRELATION.get((right, left), 0.0))
