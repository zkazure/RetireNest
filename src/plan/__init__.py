"""plan：基础退休规划的聚合测算。

本期只消费 12 个基础字段；医疗、养老、存款和生活偏好由各自命令测算。
"""

from plan.engine import build_explanation, build_scenarios, calculate
from plan.models import FieldError, PlanInput, PlanResult, ProjectionPoint, Scenario
from plan.payload import input_payload, result_payload, scenario_payload
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
    "input_payload",
    "result_payload",
    "scenario_payload",
    "validate",
]
