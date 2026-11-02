"""命令注册表与执行入口。"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from commands.adapters import COMMANDS
from commands.errors import CommandInputError, CommandNotFound, CommandVersionMismatch
from commands.models import Command, CommandManifest
from commands.validation import coerce_inputs

PROTOCOL_VERSION = "1.1.0"
"""命令清单协议的版本，不等同于单个命令的版本。

1.1 增加 InputSpec.description、OutputSpec.description 与
CommandManifest.when_to_use / when_not_to_use，供 LLM 工具 schema 使用；
新增字段都是可选的，命令的执行语义不变。
"""

_COMMANDS: dict[str, Command] = {command.manifest.id: command for command in COMMANDS}


def list_commands() -> list[Command]:
    return list(_COMMANDS.values())


def get_command(command_id: str) -> Command | None:
    return _COMMANDS.get(command_id)


def manifest_to_dict(manifest: CommandManifest) -> dict[str, Any]:
    return asdict(manifest)


def execute_command(command_id: str, version: str, raw_inputs: dict[str, Any]) -> dict[str, Any]:
    """校验版本与输入，执行一个命令并返回 outputs。"""
    command = get_command(command_id)
    if command is None:
        raise CommandNotFound(command_id)
    if version != command.manifest.version:
        raise CommandVersionMismatch(command_id, version)

    coerced, errors = coerce_inputs(command.manifest, raw_inputs)
    if errors:
        raise CommandInputError("请检查输入。", errors)
    return dict(command.handler(coerced))
