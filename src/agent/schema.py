"""把命令 manifest 转成 OpenAI 兼容的工具 schema。

命令是唯一能力表：工具名、参数、单位、约束、何时使用都从 manifest 生成，
避免前端、LLM 和文档各自维护一份定义。
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from agent.models import ToolCatalog, ToolSpec
from commands import Command, list_commands
from commands.models import CommandManifest, InputSpec

_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")
_DECIMAL_PATTERN = r"^-?\d+(?:\.\d+)?$"
_MAX_NAME_LENGTH = 64


def tool_name(command_id: str) -> str:
    """OpenAI 工具名只允许字母、数字、下划线和连字符，点号要换掉。"""
    name = _NAME_PATTERN.sub("_", command_id)
    if not name or len(name) > _MAX_NAME_LENGTH:
        raise ValueError(f"命令 ID 无法生成合法工具名：{command_id}")
    return name


def _description_with_unit(spec: InputSpec) -> str:
    base = (spec.description or spec.question).strip().rstrip("。；;？?！!")
    parts = [base] if base else []
    if spec.unit:
        parts.append(f"单位：{spec.unit}")
    minimum = spec.constraints.get("min")
    maximum = spec.constraints.get("max")
    if minimum is not None and maximum is not None and spec.type in (
        "integer",
        "number",
        "decimal",
    ):
        parts.append(f"范围：{minimum}–{maximum}")
    if spec.type == "decimal" and "precision" in spec.constraints:
        parts.append(f"最多 {spec.constraints['precision']} 位小数")
    if spec.required_when:
        field = spec.required_when.get("field")
        equals = spec.required_when.get("equals")
        parts.append(f"当 {field}={equals} 时必填")
    if not spec.required:
        parts.append("可选")
    return "；".join(part.strip("；") for part in parts if part)


def _json_type(spec: InputSpec) -> str:
    mapping = {
        "integer": "integer",
        "number": "number",
        "decimal": "string",
        "date": "string",
        "enum": "string",
        "boolean": "boolean",
        "text": "string",
    }
    if spec.type not in mapping:
        raise ValueError(f"不支持的输入类型：{spec.type}")
    return mapping[spec.type]


def input_schema(spec: InputSpec) -> dict[str, Any]:
    """单个参数的 JSON Schema；不确定的约束写进 description。"""
    schema: dict[str, Any] = {
        "type": _json_type(spec),
        "description": _description_with_unit(spec),
    }
    if spec.type == "enum":
        if not spec.options:
            raise ValueError(f"枚举输入 {spec.name} 缺少 options。")
        schema["enum"] = list(spec.options)
    if spec.type == "decimal":
        schema["pattern"] = _DECIMAL_PATTERN
    if spec.type == "date":
        schema["format"] = "date"
    if spec.type == "text" and "max_length" in spec.constraints:
        schema["maxLength"] = int(spec.constraints["max_length"])
    if spec.type in ("integer", "number"):
        if "min" in spec.constraints:
            schema["minimum"] = spec.constraints["min"]
        if "max" in spec.constraints:
            schema["maximum"] = spec.constraints["max"]
    if spec.default is not None:
        schema["default"] = spec.default
    return schema


def _tool_description(manifest: CommandManifest) -> str:
    lines = [manifest.question]
    if manifest.description:
        lines.append(manifest.description)
    if manifest.when_to_use:
        lines.append(f"何时使用：{manifest.when_to_use}")
    if manifest.when_not_to_use:
        lines.append(f"何时不要用：{manifest.when_not_to_use}")
    visible = [spec for spec in manifest.outputs if spec.visible][:8]
    if visible:
        outputs = "、".join(f"{spec.name}（{spec.question}）" for spec in visible)
        lines.append(f"主要输出：{outputs}")
    lines.append(
        "金额单位元；收益率与通胀率用数字百分数（5 表示 5%）；"
        "金额口径以字段名和工具说明为准（_real 实际值，_nominal 名义值）。"
    )
    return "\n".join(lines)


def build_tool_spec(command: Command) -> ToolSpec:
    manifest = command.manifest
    properties = {spec.name: input_schema(spec) for spec in manifest.inputs}
    required = [spec.name for spec in manifest.inputs if spec.required]
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
    return ToolSpec(
        name=tool_name(manifest.id),
        command_id=manifest.id,
        version=manifest.version,
        description=_tool_description(manifest),
        parameters=parameters,
        when_to_use=manifest.when_to_use,
    )


def build_catalog(commands: Iterable[Command] | None = None) -> ToolCatalog:
    """从注册表生成工具目录；默认包含全部命令。"""
    selected = list(commands) if commands is not None else list_commands()
    specs = tuple(build_tool_spec(command) for command in selected)
    names = [spec.name for spec in specs]
    if len(names) != len(set(names)):
        raise ValueError("工具名重复，检查命令 ID。")
    return ToolCatalog(specs=specs)
