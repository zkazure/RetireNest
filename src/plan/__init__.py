"""plan：退休规划共用的数据结构。

计算已迁到专门模块（`lifecycle`、`savings`、`pension` 等），这里只保留领域错误类型，
供命令校验、页面解析与 API 错误映射共用。
"""

from plan.models import FieldError, PlanInput, PlanResult, ProjectionPoint, Scenario

__all__ = [
    "FieldError",
    "PlanInput",
    "PlanResult",
    "ProjectionPoint",
    "Scenario",
]
