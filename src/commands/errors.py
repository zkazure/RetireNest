"""命令层错误。

命令错误只描述输入/执行问题；HTTP 状态码由 API 层读取。
"""

from __future__ import annotations

from plan.models import FieldError


class CommandError(Exception):
    status = 500
    code = "COMMAND_FAILED"

    def __init__(
        self,
        message: str,
        field_errors: list[FieldError] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or []


class CommandInputError(CommandError):
    status = 422
    code = "INVALID_INPUT"


class CommandNotFound(CommandError):
    status = 404
    code = "UNKNOWN_COMMAND"

    def __init__(self, command_id: str) -> None:
        super().__init__(f"未知命令：{command_id}")


class CommandVersionMismatch(CommandError):
    status = 409
    code = "UNSUPPORTED_VERSION"

    def __init__(self, command_id: str, version: str) -> None:
        super().__init__(f"命令 {command_id} 不支持版本 {version}。")


class CommandExecutionError(CommandError):
    status = 500
    code = "COMMAND_FAILED"
