"""profit：退休规划里的被动收入计算。

目前只有银行活期存款收益，见 demand_deposit；缺省利率来自 rates 里的快照。
"""

from profit.demand_deposit import (
    DAYS_PER_YEAR,
    DEFAULT_ANNUAL_RATE,
    DemandDeposit,
    DemandDepositResult,
    calculate,
)
from profit.errors import ProfitError
from profit.rates import SNAPSHOT, RateQuote, average_rate, is_stale

__all__ = [
    "DAYS_PER_YEAR",
    "DEFAULT_ANNUAL_RATE",
    "SNAPSHOT",
    "DemandDeposit",
    "DemandDepositResult",
    "ProfitError",
    "RateQuote",
    "average_rate",
    "calculate",
    "is_stale",
]
