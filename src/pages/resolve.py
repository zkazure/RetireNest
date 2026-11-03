"""把页面清单解析成前端可直接渲染的 JSON。

解析时做三件事：

1. 校验页面定义：引用存在、字段不重复、没有死字段或悬空参数、规则指向真实字段；
   页面标为可留空的字段，消费它的命令也必须允许省略。字段是否必答只由页面
   清单的 `required` 决定，不再从命令输入推导。
2. 取字段文案：label 只能来自 manifest 的 question，页面模块不能自带问题文本。
3. 合并约束：同一字段被多个命令消费时，min/max/precision/max_length 取交集，
   每次请求现算，前端因此不需要持有任何数值常量。
4. 校验示例画像：`presets` 里的每个取值都要对得上页面字段与它的类型、选项与
   约束，坏画像在解析阶段就报错，不留给前端猜。
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date
from typing import Any

from commands import Command, get_command
from commands.models import InputSpec
from commands.validation import DECIMAL_RE
from pages.models import PageError, PageField, PageManifest

_LOOKUP = Callable[[str], Command | None]

_CONTROL_TYPES = {
    "integer": "number",
    "number": "number",
    "decimal": "decimal",
    "date": "date",
    "enum": "select",
    "boolean": "checkbox",
    "text": "text",
    "tier": "tier",
}

# 页面上渲染的是来源命令的类型；消费命令必须能接受这个类型的取值。
_COMPATIBLE = {
    "integer": {"integer", "number"},
    "number": {"number"},
    "decimal": {"decimal"},
    "date": {"date"},
    "enum": {"enum", "text"},
    "boolean": {"boolean"},
    "text": {"text"},
    "tier": {"tier"},
}


def _specs(manifest: Any) -> dict[str, InputSpec]:
    return {spec.name: spec for spec in manifest.inputs}


def resolve(page: PageManifest, lookup: _LOOKUP = get_command) -> dict[str, Any]:
    """解析页面；定义不合法时抛 `PageError`。"""
    manifests: dict[str, Any] = {}
    for execution in page.executions:
        command = lookup(execution.command)
        if command is None:
            raise PageError(f"执行清单引用了未知命令：{execution.command}")
        manifests[execution.command] = command.manifest

    specs_by_command = {
        command_id: _specs(manifest) for command_id, manifest in manifests.items()
    }

    consumers: dict[str, list[tuple[Any, InputSpec]]] = {}
    for execution in page.executions:
        specs = specs_by_command[execution.command]
        for argument, field_name in execution.inputs.items():
            spec = specs.get(argument)
            if spec is None:
                raise PageError(f"命令 {execution.command} 没有参数 {argument}")
            consumers.setdefault(field_name, []).append((manifests[execution.command], spec))

    fields = page.fields()
    names = [field.name for field in fields]
    if len(set(names)) != len(names):
        raise PageError("页面字段名重复。")
    by_name = {field.name: field for field in fields}

    toggles = {toggle.name for toggle in page.toggles()}
    if toggles & set(names):
        raise PageError("分组开关与字段重名。")
    for execution in page.executions:
        if execution.toggle is not None and execution.toggle not in toggles:
            raise PageError(f"执行清单引用了未知开关：{execution.toggle}")

    for rule in page.rules:
        for name in (rule.left, rule.right):
            if name not in by_name:
                raise PageError(f"跨字段规则引用了未知字段：{name}")

    resolved_fields: dict[str, dict[str, Any]] = {}
    for field in fields:
        resolved_fields[field.name] = _resolve_field(field, consumers, specs_by_command)

    presets = _presets(page, resolved_fields)

    return {
        "id": page.id,
        "version": page.version,
        "title": page.title,
        "description": page.description,
        "sections": [
            {
                "id": section.id,
                "title": section.title,
                "description": section.description,
                "toggle": (
                    None
                    if section.toggle is None
                    else {
                        "name": section.toggle.name,
                        "label": section.toggle.label,
                        "defaultValue": section.toggle.default,
                    }
                ),
                "fields": [resolved_fields[field.name] for field in section.fields],
            }
            for section in page.sections
        ],
        "executions": [
            {
                "command": execution.command,
                "version": manifests[execution.command].version,
                "question": manifests[execution.command].question,
                "description": manifests[execution.command].description,
                "inputs": dict(execution.inputs),
                "toggle": execution.toggle,
                "outputs": [
                    {
                        "name": output.name,
                        "question": output.question,
                        "type": output.type,
                        "unit": output.unit,
                        "precision": output.precision,
                        "semantic": output.semantic,
                        "visible": output.visible,
                        **(
                            {}
                            if output.time_axis is None
                            else {"time_axis": dict(output.time_axis)}
                        ),
                    }
                    for output in manifests[execution.command].outputs
                ],
            }
            for execution in page.executions
        ],
        "rules": [
            {
                "type": rule.type,
                "left": rule.left,
                "right": rule.right,
                "message": rule.message,
                **({} if rule.minimum is None else {"minimum": rule.minimum}),
            }
            for rule in page.rules
        ],
        "presets": presets,
    }


def _resolve_field(
    field: PageField,
    consumers: dict[str, list[tuple[Any, InputSpec]]],
    specs_by_command: dict[str, dict[str, InputSpec]],
) -> dict[str, Any]:
    field_consumers = consumers.get(field.name)
    if not field_consumers:
        raise PageError(f"字段没有被任何命令使用：{field.name}")

    source_spec = specs_by_command.get(field.command, {}).get(field.source_input)
    if source_spec is None:
        raise PageError(f"字段 {field.name} 的来源命令 {field.command} 没有输入 {field.source_input}")

    sources = [
        spec
        for manifest, spec in field_consumers
        if manifest.id == field.command and spec.name == field.source_input
    ]
    if not sources:
        raise PageError(f"字段 {field.name} 的来源命令没有消费它。")

    for manifest, spec in field_consumers:
        allowed = _COMPATIBLE.get(source_spec.type)
        if allowed is None:
            raise PageError(f"不支持的输入类型：{source_spec.type}")
        if spec.type not in allowed:
            raise PageError(
                f"字段 {field.name} 在 {manifest.id} 里是 {spec.type}，"
                f"无法接受页面渲染的 {source_spec.type}。"
            )

    constraints = _intersect(field.name, [spec for _, spec in field_consumers])
    if not field.required:
        for manifest, spec in field_consumers:
            if spec.required or spec.required_when:
                raise PageError(
                    f"字段 {field.name} 在页面上可留空，但命令 {manifest.id} 要求必填。"
                )
    required = field.required
    if source_spec.type == "tier" and field.allow_custom:
        for manifest, spec in field_consumers:
            if not spec.allow_custom:
                raise PageError(
                    f"字段 {field.name} 允许自行填写，但命令 {manifest.id} 只接受档位选项。"
                )

    payload: dict[str, Any] = {
        "name": field.name,
        "label": source_spec.question,
        "type": _CONTROL_TYPES[source_spec.type],
        "required": required,
        "source": {"command": field.command, "input": field.source_input},
    }
    if source_spec.type == "integer" or (
        source_spec.type == "tier" and constraints.get("integer")
    ):
        payload["integer"] = True
    if source_spec.unit:
        payload["unit"] = source_spec.unit
    default = source_spec.default
    if default is None:
        default = next(
            (spec.default for _, spec in field_consumers if spec.default is not None), None
        )
    if default is not None:
        payload["defaultValue"] = default
    for key, target in (
        ("min", "min"),
        ("max", "max"),
        ("precision", "precision"),
        ("max_length", "maxLength"),
    ):
        if key in constraints:
            payload[target] = constraints[key]
    if source_spec.type == "tier":
        payload["tiers"] = _tier_payload(field.name, [spec for _, spec in field_consumers])
        payload["allowCustom"] = field.allow_custom
    if source_spec.type == "enum":
        if not source_spec.options:
            raise PageError(f"字段 {field.name} 是枚举但没有选项。")
        payload["options"] = [{"label": option, "value": option} for option in source_spec.options]
        payload["allowCustom"] = False
    if field.derive:
        payload["derive"] = field.derive
    if field.hint:
        payload["hint"] = field.hint
    if field.visible_when:
        payload["visibleWhen"] = [dict(condition) for condition in field.visible_when]
    return payload


def _tier_payload(field_name: str, specs: list[InputSpec]) -> list[dict[str, Any]]:
    """同一字段被多个命令消费时，档位表必须完全一致，否则界面回显会对不上。"""
    reference = [(tier.value, tier.label, tier.amount) for tier in specs[0].tiers]
    if not reference:
        raise PageError(f"字段 {field_name} 是档位输入但没有选项。")
    for spec in specs[1:]:
        current = [(tier.value, tier.label, tier.amount) for tier in spec.tiers]
        if current != reference:
            raise PageError(f"字段 {field_name} 在不同命令里的档位表不一致。")
    return [
        {"value": tier.value, "label": tier.label, "amount": tier.amount}
        for tier in specs[0].tiers
    ]


def _intersect(field_name: str, specs: list[InputSpec]) -> dict[str, Any]:
    """对同一字段的所有约束取交集；交集为空说明页面定义自相矛盾。"""
    mins = [spec.constraints["min"] for spec in specs if "min" in spec.constraints]
    maxs = [spec.constraints["max"] for spec in specs if "max" in spec.constraints]
    precisions = [
        spec.constraints["precision"] for spec in specs if "precision" in spec.constraints
    ]
    lengths = [
        spec.constraints["max_length"] for spec in specs if "max_length" in spec.constraints
    ]

    constraints: dict[str, Any] = {}
    if mins:
        constraints["min"] = max(mins)
    if maxs:
        constraints["max"] = min(maxs)
    if precisions:
        constraints["precision"] = min(precisions)
    if lengths:
        constraints["max_length"] = min(lengths)
    if any(spec.constraints.get("integer") for spec in specs):
        constraints["integer"] = True
    if "min" in constraints and "max" in constraints and constraints["min"] > constraints["max"]:
        raise PageError(
            f"字段 {field_name} 的约束没有交集："
            f"min={constraints['min']}，max={constraints['max']}。"
        )
    return constraints


def _presets(
    page: PageManifest, resolved_fields: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """校验示例画像并整理成下发结构；允许只填一部分字段。"""
    seen: set[str] = set()
    payload: list[dict[str, Any]] = []
    for preset in page.presets:
        if not preset.id:
            raise PageError("示例画像缺少 id。")
        if preset.id in seen:
            raise PageError(f"示例画像 id 重复：{preset.id}")
        seen.add(preset.id)
        if not preset.label.strip():
            raise PageError(f"示例画像 {preset.id} 缺少名称。")
        for name, value in preset.values.items():
            field = resolved_fields.get(name)
            if field is None:
                raise PageError(f"示例画像 {preset.id} 引用了未知字段：{name}")
            problem = _preset_value_problem(field, value)
            if problem:
                raise PageError(f"示例画像 {preset.id} 的字段 {name} {problem}")
        item: dict[str, Any] = {
            "id": preset.id,
            "label": preset.label,
            "values": dict(preset.values),
        }
        if preset.description:
            item["description"] = preset.description
        payload.append(item)
    return payload


def _preset_value_problem(field: dict[str, Any], value: str | bool) -> str | None:
    """按字段的下发结构挑错；返回 None 表示这个取值可以用。"""
    kind = field["type"]
    if kind == "checkbox":
        return None if isinstance(value, bool) else "应该是布尔值。"
    if not isinstance(value, str):
        return "应该是字符串。"
    if kind == "select":
        if value in {option["value"] for option in field.get("options", [])}:
            return None
        if field.get("allowCustom"):
            return None
        return f"不在选项里：{value}"
    if kind == "date":
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return f"不是合法日期：{value}"
        return None if parsed.isoformat() == value else f"不是合法日期：{value}"
    if kind == "tier":
        if value in {tier["value"] for tier in field.get("tiers", [])}:
            return None
        if not field.get("allowCustom"):
            return f"不在档位里：{value}"
        return _number_problem(field, value)
    if kind in {"number", "decimal"}:
        return _number_problem(field, value)
    if kind in {"text", "textarea"}:
        if not value.strip():
            return "不能为空。"
        max_length = field.get("maxLength")
        return None if max_length is None or len(value) <= max_length else f"超过 {max_length} 个字符。"
    return f"不支持的类型：{kind}"


def _number_problem(field: dict[str, Any], value: str) -> str | None:
    text = value.strip()
    if not DECIMAL_RE.fullmatch(text):
        return f"不是数字：{value}"
    number = float(text)
    if not math.isfinite(number):
        return f"不是有限数字：{value}"
    if field.get("integer") and not number.is_integer():
        return f"不是整数：{value}"
    minimum = field.get("min")
    if minimum is not None and number < minimum:
        return f"小于下限 {minimum}：{value}"
    maximum = field.get("max")
    if maximum is not None and number > maximum:
        return f"大于上限 {maximum}：{value}"
    return None
