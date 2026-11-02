"""Agent 服务：配置、鉴权、会话、循环与最终回复的组装。"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Mapping
from typing import Any

from agent.auth import AgentAuth
from agent.client import OpenAIChatClient
from agent.config import LLMConfig
from agent.errors import AgentDisabled, AgentUnauthorized
from agent.fake import DemoChatClient
from agent.loop import run_agent
from agent.models import AgentReply, ChatClient, ToolCatalog
from agent.prompt import build_system_prompt
from agent.schema import build_catalog
from agent.session import SessionBackend, SessionStore, SqliteSessionStore

logger = logging.getLogger(__name__)

MAX_STORED_MESSAGES = 40
"""会话里最多保留的消息条数；从一条 user 消息开始截断，避免孤立的 tool 消息。"""

DB_ENV = "RETIRENEST_AGENT_DB"
FAKE_ENV = "RETIRENEST_AGENT_FAKE"


def trim_messages(
    messages: list[dict[str, Any]],
    max_messages: int = MAX_STORED_MESSAGES,
) -> list[dict[str, Any]]:
    if max_messages <= 0:
        raise ValueError("max_messages 必须大于 0。")
    if len(messages) <= max_messages:
        return messages
    start = len(messages) - max_messages
    while start < len(messages) and messages[start].get("role") != "user":
        start += 1
    if start >= len(messages):
        return messages[-max_messages:]
    return messages[start:]


class AgentService:
    """一次对话 = 读会话 + 跑工具循环 + 写回历史。"""

    def __init__(
        self,
        config: LLMConfig,
        *,
        client: ChatClient | None = None,
        sessions: SessionBackend | None = None,
        catalog: ToolCatalog | None = None,
        auth: AgentAuth | None = None,
    ) -> None:
        self.config = config
        self._client = client
        self.sessions = sessions or SessionStore()
        self.catalog = catalog or build_catalog()
        self.auth = auth or AgentAuth()
        self._model_name = config.model or getattr(client, "model_name", "fake")

    @property
    def enabled(self) -> bool:
        """配置了模型 key，或注入了假模型（开发演示/测试），就允许对话。"""
        return self.config.enabled or self._client is not None

    @property
    def model_name(self) -> str:
        return self._model_name

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AgentService:
        source = os.environ if environ is None else environ
        config = LLMConfig.from_env(source)
        auth = AgentAuth.from_env(source)
        fake = source.get(FAKE_ENV, "").strip() == "1"
        database = source.get(DB_ENV, "").strip()
        sessions: SessionBackend = SqliteSessionStore(database) if database else SessionStore()
        return cls(
            config=config,
            client=DemoChatClient() if fake else None,
            sessions=sessions,
            auth=auth,
        )

    @property
    def client(self) -> ChatClient:
        if self._client is None:
            if not self.config.enabled:
                raise AgentDisabled(self.config.missing)
            self._client = OpenAIChatClient(self.config)
        return self._client

    def chat(
        self,
        session_id: str | None,
        message: str,
        *,
        user: str | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        override: LLMConfig | None = None,
    ) -> AgentReply:
        """跑一轮对话。

        `override` 来自设置页随请求带来的密钥：只用于这一轮，不写进 service，
        也不落日志；服务端环境变量仍是兜底。
        """
        if not self.enabled and override is None:
            raise AgentDisabled(self.config.missing)
        if self.auth.enabled and not user:
            raise AgentUnauthorized("缺少访问令牌。")

        owner = user if self.auth.enabled else None
        session = self.sessions.get_or_create(session_id, owner=owner)
        with session.lock:
            self._emit(on_event, {"type": "session", "session_id": session.id})
            conversation: list[dict[str, Any]] = [
                {"role": "system", "content": build_system_prompt(self.catalog)}
            ]
            conversation.extend(session.messages)
            conversation.append({"role": "user", "content": message})
            client = self._client_for(override)
            run = run_agent(conversation, client, self.catalog, on_event=on_event)
            session.messages = trim_messages(conversation[1:])
            session.updated_at = time.time()
            self.sessions.save(session)
            return AgentReply(
                session_id=session.id,
                reply=run.reply,
                tool_calls=run.tool_calls,
                warnings=run.warnings,
                model=override.model if override is not None and override.model else self._model_name,
            )

    def _client_for(self, override: LLMConfig | None) -> ChatClient:
        if override is None:
            return self.client
        if not override.enabled:
            raise AgentDisabled(override.missing)
        return OpenAIChatClient(override)

    def reset(self, session_id: str, user: str | None = None) -> bool:
        owner = user if self.auth.enabled else None
        return self.sessions.reset(session_id, owner=owner)

    @staticmethod
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
