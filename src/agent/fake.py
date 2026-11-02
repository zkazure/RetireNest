"""假模型：只用于测试和本地演示，不是 LLM，也不做任何推理。

- `ScriptedChatClient`：按脚本返回，测试用。
- `DemoChatClient`：固定调用一次 `savings.project` 再给最终文本；没有 provider
  key 时也能在页面上跑通工具轨迹，但数字是固定示例，不能用于真实规划。
"""

from __future__ import annotations

import json
from typing import Any

from agent.models import AssistantTurn, ToolCall

DEMO_ARGS = {
    "current_savings": 500_000,
    "monthly_contribution": 3_000,
    "annual_return_pct": 5,
    "inflation_pct": 2,
    "years": 20,
}


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


class DemoChatClient:
    """无 key 时跑通 UI 的固定演示客户端。"""

    model_name = "fake-demo"

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantTurn:
        self.requests.append({"messages": list(messages), "tools": list(tools)})
        if not tools:
            return AssistantTurn("（开发假模型）已停止工具调用。", ())

        last_user = max(
            (index for index, message in enumerate(messages) if message.get("role") == "user"),
            default=-1,
        )
        tool_messages = [
            message
            for message in messages[last_user + 1 :]
            if message.get("role") == "tool"
        ]
        if tool_messages:
            return AssistantTurn(self._final_text(tool_messages[-1]), ())

        return AssistantTurn(
            "（开发假模型）我先用一组固定示例调用储蓄工具，数字不是你的情况。",
            (ToolCall(id="demo_call", name="savings_project", arguments=json.dumps(DEMO_ARGS)),),
        )

    @staticmethod
    def _final_text(tool_message: dict[str, Any]) -> str:
        try:
            payload = json.loads(str(tool_message.get("content", "{}")))
        except json.JSONDecodeError:
            payload = {}
        outputs = payload.get("outputs") if isinstance(payload, dict) else None
        amount = outputs.get("future_balance_real") if isinstance(outputs, dict) else None
        if isinstance(amount, (int, float)):
            return (
                "（开发假模型）这是固定示例，不是真实测算：按每月 3000 元、"
                f"名义年回报 5%、通胀 2%、20 年，实际余额约 {amount:,.0f} 元。"
                "配置真实模型后，请以工具结果和你的实际参数为准。"
            )
        return "（开发假模型）工具没有返回可读结果，请检查服务端日志。"
