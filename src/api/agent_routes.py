"""Agent 对话端点。

会话与模型调用都在 `agent` 包内；这里只做请求校验、错误映射和响应组装。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent import AgentDisabled, AgentError, AgentService, AgentUpstreamError
from api.errors import ApiError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent"])


class AgentChatRequest(BaseModel):
    """一次对话请求；省略 session_id 时由服务端生成并回显。"""

    model_config = ConfigDict(extra="forbid")

    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message 不能为空。")
        return value


@router.post("/api/agent/chat")
def chat(request: AgentChatRequest, http_request: Request) -> dict[str, Any]:
    service: AgentService | None = getattr(http_request.app.state, "agent_service", None)
    if service is None:
        raise ApiError(503, "AGENT_DISABLED", "Agent 未初始化。")

    try:
        reply = service.chat(request.session_id, request.message)
    except AgentDisabled as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc
    except AgentUpstreamError as exc:
        logger.warning("Agent 上游调用失败：%s", type(exc).__name__)
        raise ApiError(exc.status, exc.code, exc.message) from exc
    except AgentError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc

    return {
        "session_id": reply.session_id,
        "reply": reply.reply,
        "tool_calls": list(reply.tool_calls),
        "warnings": list(reply.warnings),
        "model": reply.model,
    }
