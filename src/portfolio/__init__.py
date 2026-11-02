"""portfolio：资产配置到组合收益与波动。

三档风险资产各自的长期收益与波动是假设，见 `assumptions`；`combine` 按配比
算组合均值与波动，结果直接喂给 `simulation` 与 `lifecycle`。
"""

from portfolio.assumptions import ASSET_CLASSES, CORRELATION, AssetClass
from portfolio.combine import Allocation, PortfolioAssumption, combine
from portfolio.errors import PortfolioError

__all__ = [
    "ASSET_CLASSES",
    "CORRELATION",
    "Allocation",
    "AssetClass",
    "PortfolioAssumption",
    "PortfolioError",
    "combine",
]
