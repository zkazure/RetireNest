"""把前端 values 映射成标准化输入，并组装成功响应。"""

from __future__ import annotations

import math
from typing import Any

from api.errors import schema_mismatch, validation_error
from api.schemas import PlanRequest
from plan import (
    PlanInput,
    build_explanation,
    build_scenarios,
    calculate,
    input_payload,
    result_payload,
    scenario_payload,
    validate,
)
from plan.models import FieldError

TEMPLATE_ID = "retirenest-retirement"
SCHEMA_VERSION = "1.0.0"

_INTEGER_FIELDS = ("age", "retire_age", "life_expectancy")
_NUMBER_FIELDS = (
    "monthly_income",
    "monthly_expense",
    "assets",
    "debt",
    "retirement_expense",
    "monthly_pension",
    "nominal_return",
    "inflation",
)
WARNINGS = (
    "医疗、养老、存款信息本期尚未参与计算。",
    "结果基于你填写的假设，不构成投资建议。",
)


def _read_city(values: dict[str, Any], errors: list[FieldError]) -> str:
    raw = values.get("city")
    if not isinstance(raw, str):
        errors.append(FieldError("city", "请填写城市。"))
        return ""
    city = raw.strip()
    if not city:
        errors.append(FieldError("city", "请填写城市。"))
    return city


def _read_integer(values: dict[str, Any], name: str, errors: list[FieldError]) -> int:
    raw = values.get(name)
    if isinstance(raw, bool) or not isinstance(raw, int):
        errors.append(FieldError(name, "请填写整数。"))
        return 0
    return raw


def _read_number(values: dict[str, Any], name: str, errors: list[FieldError]) -> float:
    raw = values.get(name)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        errors.append(FieldError(name, "请填写有效数字。"))
        return 0.0
    value = float(raw)
    if not math.isfinite(value):
        errors.append(FieldError(name, "请填写有效数字。"))
        return 0.0
    return value


def parse_values(values: dict[str, Any]) -> tuple[PlanInput | None, list[FieldError]]:
    """只读取 12 个基础字段；未知字段（扩展模块）静默忽略。"""
    errors: list[FieldError] = []
    if not isinstance(values, dict):
        return None, [FieldError("values", "请求数据格式无效。")]

    city = _read_city(values, errors)
    integers = {name: _read_integer(values, name, errors) for name in _INTEGER_FIELDS}
    numbers = {name: _read_number(values, name, errors) for name in _NUMBER_FIELDS}
    if errors:
        return None, errors

    return (
        PlanInput(
            city=city,
            age=integers["age"],
            retirement_age=integers["retire_age"],
            life_expectancy=integers["life_expectancy"],
            monthly_income=numbers["monthly_income"],
            monthly_expense=numbers["monthly_expense"],
            assets=numbers["assets"],
            debt=numbers["debt"],
            retirement_expense=numbers["retirement_expense"],
            monthly_pension=numbers["monthly_pension"],
            nominal_return=numbers["nominal_return"],
            inflation=numbers["inflation"],
        ),
        [],
    )


def build_plan_response(request: PlanRequest) -> dict[str, object]:
    """校验版本和 values，计算并返回 PlanResponse 同构的 dict。"""
    if request.template_id != TEMPLATE_ID or request.schema_version != SCHEMA_VERSION:
        raise schema_mismatch()

    plan_input, errors = parse_values(request.values)
    if plan_input is not None:
        errors.extend(validate(plan_input))
    if plan_input is None or errors:
        raise validation_error(errors)

    result = calculate(plan_input)
    scenarios = build_scenarios(plan_input)
    return {
        "template_id": TEMPLATE_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": "backend",
        "plan_input": input_payload(plan_input),
        "result": result_payload(result),
        "scenarios": [scenario_payload(scenario) for scenario in scenarios],
        "explanation": build_explanation(plan_input, result),
        "warnings": list(WARNINGS),
    }
