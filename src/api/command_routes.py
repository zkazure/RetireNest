"""命令发现与执行端点。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from api.errors import ApiError
from commands import (
    PROTOCOL_VERSION,
    execute_command,
    get_command,
    list_commands,
    manifest_to_dict,
)
from commands.errors import CommandError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/commands", tags=["commands"])


class CommandRequest(BaseModel):
    """单命令执行请求；顶层只允许 version 和 inputs。"""

    model_config = ConfigDict(extra="forbid")

    version: str
    inputs: dict[str, Any]


@router.get("")
def list_commands_endpoint() -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "commands": [manifest_to_dict(command.manifest) for command in list_commands()],
    }


@router.post("/{command_id}")
def execute_command_endpoint(command_id: str, request: CommandRequest) -> dict[str, Any]:
    try:
        outputs = execute_command(command_id, request.version, request.inputs)
    except CommandError as exc:
        raise ApiError(exc.status, exc.code, exc.message, exc.field_errors) from exc
    except Exception as exc:
        logger.exception("Unhandled command error: %s", command_id, exc_info=exc)
        raise ApiError(500, "COMMAND_FAILED", "命令执行失败，请稍后重试。") from exc

    command = get_command(command_id)
    if command is None:  # execute_command 已保证存在；防御性分支。
        raise ApiError(404, "UNKNOWN_COMMAND", f"未知命令：{command_id}")
    return {
        "command_id": command_id,
        "version": command.manifest.version,
        "outputs": outputs,
        "meta": {
            "deterministic": command.manifest.deterministic,
            "as_of": command.manifest.as_of,
        },
    }
