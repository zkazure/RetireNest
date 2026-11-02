"""Agent 对话端点：普通 JSON、SSE 事件流与会话重置。

会话与模型调用都在 `agent` 包内；这里只做请求校验、鉴权、错误映射和响应组装。
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent import AgentDisabled, AgentError, AgentService
from agent.models import AgentReply
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


def _service(request: Request) -> AgentService:
    service: AgentService | None = getattr(request.app.state, "agent_service", None)
    if service is None:
        raise ApiError(503, "AGENT_DISABLED", "Agent 未初始化。")
    return service


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return value.strip() or None


def _resolve_user(service: AgentService, request: Request) -> str | None:
    return service.auth.user_for(_bearer_token(request))


def _reply_payload(reply: AgentReply) -> dict[str, Any]:
    return {
        "session_id": reply.session_id,
        "reply": reply.reply,
        "tool_calls": list(reply.tool_calls),
        "warnings": list(reply.warnings),
        "model": reply.model,
    }


def _api_error(exc: AgentError) -> ApiError:
    return ApiError(exc.status, exc.code, exc.message)


@router.post("/api/agent/chat")
def chat(request: AgentChatRequest, http_request: Request) -> dict[str, Any]:
    service = _service(http_request)
    try:
        user = _resolve_user(service, http_request)
        reply = service.chat(request.session_id, request.message, user=user)
    except AgentError as exc:
        raise _api_error(exc) from exc
    return _reply_payload(reply)


@router.post("/api/agent/chat/stream")
def chat_stream(request: AgentChatRequest, http_request: Request) -> StreamingResponse:
    service = _service(http_request)
    if not service.enabled:
        raise _api_error(AgentDisabled(service.config.missing))
    try:
        user = _resolve_user(service, http_request)
    except AgentError as exc:
        raise _api_error(exc) from exc

    def generate():
        events: queue.Queue[dict[str, Any] | None] = queue.Queue()

        def worker() -> None:
            try:
                reply = service.chat(
                    request.session_id,
                    request.message,
                    user=user,
                    on_event=events.put,
                )
                events.put({"type": "reply", **_reply_payload(reply)})
                events.put({"type": "done", "session_id": reply.session_id})
            except AgentError as exc:
                events.put({"type": "error", "code": exc.code, "message": exc.message})
            except Exception:
                logger.exception("Agent 流式执行失败")
                events.put(
                    {
                        "type": "error",
                        "code": "AGENT_ERROR",
                        "message": "Agent 执行失败，请稍后重试。",
                    }
                )
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True).start()
        while True:
            event = events.get()
            if event is None:
                break
            yield _sse(event)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/api/agent/sessions/{session_id}")
def reset_session(session_id: str, http_request: Request) -> dict[str, Any]:
    service = _service(http_request)
    try:
        user = _resolve_user(service, http_request)
    except AgentError as exc:
        raise _api_error(exc) from exc
    if not service.reset(session_id, user=user):
        raise ApiError(404, "AGENT_SESSION_NOT_FOUND", "会话不存在或不属于当前用户。")
    return {"session_id": session_id, "reset": True}


def _sse(event: dict[str, Any]) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
