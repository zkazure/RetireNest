"""脚本化假模型：只用于测试和本地接线，不是 LLM，也不做任何推理。

按顺序返回预先写好的 `AssistantTurn`，并记录每次请求，便于断言循环把哪些
消息与工具结果回灌给了模型。
"""

from __future__ import annotations

from typing import Any

from agent.models import AssistantTurn


class ScriptedChatClient:
    """按脚本返回回复的假客户端。"""

    def __init__(self, turns: list[AssistantTurn]) -> None:
        self._turns = list(turns)
        self.requests: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantTurn:
        self.requests.append({"messages": list(messages), "tools": list(tools)})
        if not self._turns:
            raise RuntimeError("脚本化假模型没有更多回复。")
        return self._turns.pop(0)
