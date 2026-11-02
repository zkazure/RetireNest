"""plan：基础退休规划的聚合测算。

本期只消费前端 12 个基础字段；医疗、养老、存款和生活偏好尚未参与。
"""

from plan.engine import build_explanation, build_scenarios, calculate
from plan.models import FieldError, PlanInput, PlanResult, ProjectionPoint, Scenario
from plan.validation import validate

__all__ = [
    "FieldError",
    "PlanInput",
    "PlanResult",
    "ProjectionPoint",
    "Scenario",
    "build_explanation",
    "build_scenarios",
    "calculate",
    "validate",
]
