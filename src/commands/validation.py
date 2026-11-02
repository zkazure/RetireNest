"""按 manifest 校验并转换命令输入。

JSON 线格式与 Python 类型在这里分开：decimal 是字符串，date 是
YYYY-MM-DD；进入 handler 前转换成 Decimal / date。
"""

from __future__ import annotations

import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from commands.models import CommandManifest, InputSpec
from plan.models import FieldError

_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _required_when(spec: InputSpec, raw_inputs: dict[str, Any]) -> bool:
    if spec.required_when is None:
        return False
    control = spec.required_when.get("field")
    expected = spec.required_when.get("equals")
    return raw_inputs.get(control) == expected


def _coerce_value(spec: InputSpec, raw: Any) -> tuple[Any, str | None]:
    if spec.type == "integer":
        if isinstance(raw, bool) or not isinstance(raw, int):
            return None, "请填写整数。"
        return raw, None

    if spec.type == "number":
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None, "请填写有效数字。"
        value = float(raw)
        if not math.isfinite(value):
            return None, "请填写有效数字。"
        return value, None

    if spec.type == "decimal":
        if not isinstance(raw, str) or not _DECIMAL_RE.fullmatch(raw.strip()):
            return None, "请输入有效小数（字符串）。"
        try:
            return Decimal(raw.strip()), None
        except InvalidOperation:
            return None, "请输入有效小数（字符串）。"

    if spec.type == "date":
        if not isinstance(raw, str):
            return None, "请输入有效日期。"
        try:
            value = date.fromisoformat(raw)
        except ValueError:
            return None, "请输入有效日期。"
        if value.isoformat() != raw:
            return None, "请输入有效日期。"
        return value, None

    if spec.type == "enum":
        if not isinstance(raw, str) or raw not in spec.options:
            return None, "请选择列表中的选项。"
        return raw, None

    if spec.type == "boolean":
        if not isinstance(raw, bool):
            return None, "请选择是或否。"
        return raw, None

    if spec.type == "text":
        if not isinstance(raw, str):
            return None, "请输入文本。"
        value = raw.strip()
        if not value:
            return None, "请填写。"
        return value, None

    return None, f"不支持的输入类型：{spec.type}"


def _check_constraints(spec: InputSpec, value: Any) -> str | None:
    constraints = spec.constraints
    if "min" in constraints and spec.type in ("integer", "number", "decimal"):
        minimum = constraints["min"]
        comparable = Decimal(str(minimum)) if isinstance(value, Decimal) else minimum
        if value < comparable:
            return f"不能小于 {minimum}。"
    if "max" in constraints and spec.type in ("integer", "number", "decimal"):
        maximum = constraints["max"]
        comparable = Decimal(str(maximum)) if isinstance(value, Decimal) else maximum
        if value > comparable:
            return f"不能大于 {maximum}。"
    if spec.type == "decimal" and "precision" in constraints:
        precision = int(constraints["precision"])
        decimals = max(0, -value.as_tuple().exponent)
        if decimals > precision:
            return f"最多保留 {precision} 位小数。"
    if spec.type == "text" and "max_length" in constraints:
        max_length = int(constraints["max_length"])
        if len(value) > max_length:
            return f"最多 {max_length} 个字符。"
    return None


def coerce_inputs(
    manifest: CommandManifest,
    raw_inputs: dict[str, Any],
) -> tuple[dict[str, Any], list[FieldError]]:
    """返回 (coerced_inputs, field_errors)；有错误时不要执行 handler。"""
    if not isinstance(raw_inputs, dict):
        return {}, [FieldError("inputs", "inputs 必须是对象。")]

    specs = {spec.name: spec for spec in manifest.inputs}
    errors: list[FieldError] = []
    for key in raw_inputs:
        if key not in specs:
            errors.append(FieldError(str(key), "未知输入字段。"))

    coerced: dict[str, Any] = {}
    for spec in manifest.inputs:
        raw = raw_inputs.get(spec.name)
        required = spec.required or _required_when(spec, raw_inputs)
        is_empty = raw is None or (isinstance(raw, str) and not raw.strip())
        if is_empty:
            if required:
                errors.append(FieldError(spec.name, "请填写。"))
            elif spec.default is not None:
                coerced[spec.name] = spec.default
            continue

        value, error = _coerce_value(spec, raw)
        if error is not None:
            errors.append(FieldError(spec.name, error))
            continue
        constraint_error = _check_constraints(spec, value)
        if constraint_error is not None:
            errors.append(FieldError(spec.name, constraint_error))
            continue
        coerced[spec.name] = value

    return coerced, errors
