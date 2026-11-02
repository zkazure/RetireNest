"""lifecycle：全周期收支仿真与风险分布。

`project` 用期望收益推一条确定性路径，`simulate` 抽收益路径给成功率与分位，
`compare` 把多个策略变体并排跑。收入、支出、医疗与软性支出都复用各自域的
口径，不在这里重写公式。
"""

from lifecycle.compare import compare
from lifecycle.errors import LifecycleError
from lifecycle.models import LifecycleResult, SimulationResult, YearRow
from lifecycle.project import INFLATION_PCT, pension_monthly, project, real_return_pct
from lifecycle.simulate import simulate

__all__ = [
    "INFLATION_PCT",
    "LifecycleError",
    "LifecycleResult",
    "SimulationResult",
    "YearRow",
    "compare",
    "pension_monthly",
    "project",
    "real_return_pct",
    "simulate",
]
