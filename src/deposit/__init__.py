"""deposit：退休规划里的被动收入计算。

目前只有银行活期存款收益，见 demand_deposit；缺省利率来自 rates 里的快照。
"""

from deposit.demand_deposit import (
    DAYS_PER_YEAR,
    DEFAULT_ANNUAL_RATE,
    DemandDeposit,
    DemandDepositResult,
    calculate,
)
from deposit.errors import DepositError
from deposit.rates import SNAPSHOT, RateQuote, average_rate, is_stale

__all__ = [
    "DAYS_PER_YEAR",
    "DEFAULT_ANNUAL_RATE",
    "SNAPSHOT",
    "DemandDeposit",
    "DemandDepositResult",
    "DepositError",
    "RateQuote",
    "average_rate",
    "calculate",
    "is_stale",
]
