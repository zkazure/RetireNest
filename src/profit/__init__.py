"""profit：退休规划里的被动收入计算。

目前只有银行活期存款收益，见 demand_deposit。
"""

from profit.demand_deposit import (
    DAYS_PER_YEAR,
    DEFAULT_ANNUAL_RATE,
    DemandDeposit,
    DemandDepositResult,
    ProfitError,
    calculate,
)

__all__ = [
    "DAYS_PER_YEAR",
    "DEFAULT_ANNUAL_RATE",
    "DemandDeposit",
    "DemandDepositResult",
    "ProfitError",
    "calculate",
]
