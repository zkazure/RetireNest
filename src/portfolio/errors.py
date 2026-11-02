"""portfolio：资产配置相关的错误。"""


class PortfolioError(ValueError):
    """配比不合法，或引用了未知风险档位。"""
