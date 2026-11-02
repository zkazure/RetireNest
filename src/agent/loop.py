"""ReAct 风格的工具循环。

模型返回文本就结束；返回工具调用就执行命令，把结果作为 tool 消息回灌，
直到得到文本或达到轮数上限。所有数字都来自 `commands.execute_command`。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from agent.models import (
    AgentRun,
    AssistantTurn,
    ChatClient,
    ToolCall,
    ToolCatalog,
)
from agent.verify import numeric_warnings
from commands import execute_command, get_command
from commands.errors import CommandError, CommandInputError

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8
MAX_TOOL_CONTENT_CHARS = 8000
TRUNCATED_SUFFIX = "…（工具输出已截断）"


def _emit(
    on_event: Callable[[dict[str, Any]], None] | None,
    event: dict[str, Any],
) -> None:
    if on_event is None:
        return
    try:
        on_event(event)
    except Exception:
        logger.exception("Agent 事件回调失败")


def _assistant_message(turn: AssistantTurn) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": turn.content or "",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in turn.tool_calls
        ],
    }


def _tool_error(
    call: ToolCall,
    *,
    code: str,
    message: str,
    command_id: str | None = None,
    version: str | None = None,
    inputs: dict[str, Any] | None = None,
    field_errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "tool_call_id": call.id,
        "tool_name": call.name,
        "command_id": command_id,
        "version": version,
        "inputs": inputs,
        "ok": False,
        "outputs": None,
        "error": {
            "code": code,
            "message": message,
            "field_errors": field_errors or [],
        },
    }


def _execute_tool_call(
    catalog: ToolCatalog,
    call: ToolCall,
) -> dict[str, Any]:
    """执行一次工具调用；任何失败都转成模型可读的错误结果。"""
    spec = catalog.by_name.get(call.name)
    if spec is None:
        return _tool_error(call, code="UNKNOWN_TOOL", message=f"未知工具：{call.name}")

    try:
        arguments = json.loads(call.arguments or "{}")
    except json.JSONDecodeError:
        return _tool_error(
            call,
            code="INVALID_ARGUMENTS",
            message="工具参数不是合法 JSON。",
            command_id=spec.command_id,
            version=spec.version,
        )
    if not isinstance(arguments, dict):
        return _tool_error(
            call,
            code="INVALID_ARGUMENTS",
            message="工具参数必须是 JSON 对象。",
            command_id=spec.command_id,
            version=spec.version,
        )

    command = get_command(spec.command_id)
    if command is None or command.manifest.version != spec.version:
        return _tool_error(
            call,
            code="UNKNOWN_TOOL",
            message="命令不存在或版本已变化。",
            command_id=spec.command_id,
            version=spec.version,
            inputs=arguments,
        )

    try:
        outputs = execute_command(spec.command_id, spec.version, arguments)
    except CommandInputError as exc:
        return _tool_error(
            call,
            code=exc.code,
            message=exc.message,
            command_id=spec.command_id,
            version=spec.version,
            inputs=arguments,
            field_errors=[
                {"field": error.field, "message": error.message}
                for error in exc.field_errors
            ],
        )
    except CommandError as exc:
        return _tool_error(
            call,
            code=exc.code,
            message=exc.message,
            command_id=spec.command_id,
            version=spec.version,
            inputs=arguments,
        )
    except Exception:
        logger.exception("Agent 工具执行失败：%s", spec.command_id)
        return _tool_error(
            call,
            code="COMMAND_FAILED",
            message="工具执行失败，请稍后重试。",
            command_id=spec.command_id,
            version=spec.version,
            inputs=arguments,
        )

    return {
        "tool_call_id": call.id,
        "tool_name": call.name,
        "command_id": spec.command_id,
        "version": spec.version,
        "inputs": arguments,
        "ok": True,
        "outputs": outputs,
        "error": None,
    }


def _truncate(text: str, limit: int = MAX_TOOL_CONTENT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + TRUNCATED_SUFFIX


def tool_content(record: dict[str, Any]) -> str:
    """把工具记录变成回灌给模型的一段文本。"""
    if record["ok"]:
        payload = {
            "ok": True,
            "command_id": record["command_id"],
            "version": record["version"],
            "outputs": record["outputs"],
        }
    else:
        payload = {
            "ok": False,
            "command_id": record["command_id"],
            "error": record["error"],
        }
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return _truncate(text)


def run_agent(
    conversation: list[dict[str, Any]],
    client: ChatClient,
    catalog: ToolCatalog,
    *,
    max_rounds: int = MAX_TOOL_ROUNDS,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> AgentRun:
    """执行循环；原地追加 assistant/tool 消息，返回最终文本与轨迹。"""
    if max_rounds <= 0:
        raise ValueError("max_rounds 必须大于 0。")

    trace: list[dict[str, Any]] = []
    warnings: list[str] = []

    for _ in range(max_rounds):
        turn = client.complete(conversation, catalog.schemas)
        if not turn.tool_calls:
            reply = turn.content or ""
            warnings.extend(numeric_warnings(reply, trace))
            conversation.append({"role": "assistant", "content": reply})
            return AgentRun(
                reply=reply,
                tool_calls=tuple(trace),
                warnings=tuple(warnings),
            )

        conversation.append(_assistant_message(turn))
        for call in turn.tool_calls:
            spec = catalog.by_name.get(call.name)
            _emit(
                on_event,
                {
                    "type": "tool_call",
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "command_id": spec.command_id if spec else None,
                },
            )
            record = _execute_tool_call(catalog, call)
            trace.append(record)
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": tool_content(record),
                }
            )
            _emit(on_event, {"type": "tool_result", **record})

    warnings.append(f"工具调用超过 {max_rounds} 轮，已停止继续调用。")
    conversation.append(
        {
            "role": "user",
            "content": "请基于已有工具结果给出最终回答，不要再调用工具。",
        }
    )
    final = client.complete(conversation, [])
    reply = final.content or "工具调用次数过多，请缩小问题范围后重试。"
    warnings.extend(numeric_warnings(reply, trace))
    conversation.append({"role": "assistant", "content": reply})
    return AgentRun(reply=reply, tool_calls=tuple(trace), warnings=tuple(warnings))
