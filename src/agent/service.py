"""Agent 服务：配置、会话、循环与最终回复的组装。"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from agent.client import OpenAIChatClient
from agent.config import LLMConfig
from agent.errors import AgentDisabled
from agent.loop import run_agent
from agent.models import AgentReply, ChatClient, ToolCatalog
from agent.prompt import build_system_prompt
from agent.schema import build_catalog
from agent.session import SessionStore

MAX_STORED_MESSAGES = 40
"""会话里最多保留的消息条数；从一条 user 消息开始截断，避免孤立的 tool 消息。"""


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
        sessions: SessionStore | None = None,
        catalog: ToolCatalog | None = None,
    ) -> None:
        self.config = config
        self._client = client
        self.sessions = sessions or SessionStore()
        self.catalog = catalog or build_catalog()

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AgentService:
        return cls(config=LLMConfig.from_env(environ))

    @property
    def client(self) -> ChatClient:
        if self._client is None:
            if not self.config.enabled:
                raise AgentDisabled(self.config.missing)
            self._client = OpenAIChatClient(self.config)
        return self._client

    def chat(self, session_id: str | None, message: str) -> AgentReply:
        if not self.config.enabled:
            raise AgentDisabled(self.config.missing)

        session = self.sessions.get_or_create(session_id)
        with session.lock:
            conversation: list[dict[str, Any]] = [
                {"role": "system", "content": build_system_prompt(self.catalog)}
            ]
            conversation.extend(session.messages)
            conversation.append({"role": "user", "content": message})
            run = run_agent(conversation, self.client, self.catalog)
            session.messages = trim_messages(conversation[1:])
            session.updated_at = time.monotonic()
            return AgentReply(
                session_id=session.id,
                reply=run.reply,
                tool_calls=run.tool_calls,
                warnings=run.warnings,
                model=self.config.model or "",
            )

    def reset(self, session_id: str) -> bool:
        return self.sessions.reset(session_id)
