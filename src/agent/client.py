"""OpenAI 兼容的模型客户端。

只依赖 `openai` SDK 的 chat.completions 接口；DeepSeek、OpenAI、Ollama 等
提供兼容端点时都可以用，通过 base_url 切换。
"""

from __future__ import annotations

from typing import Any

from agent.config import LLMConfig
from agent.errors import AgentUpstreamError
from agent.models import AssistantTurn, ToolCall

DEFAULT_TEMPERATURE = 0.2


class OpenAIChatClient:
    """把 SDK 响应收敛成 Agent 层自己的 `AssistantTurn`。"""

    def __init__(self, config: LLMConfig) -> None:
        if not config.enabled:
            raise ValueError("未配置 API key 或模型名。")
        from openai import OpenAI

        options: dict[str, Any] = {
            "api_key": config.api_key,
            "timeout": config.timeout_seconds,
        }
        if config.base_url:
            options["base_url"] = config.base_url
        self._client = OpenAI(**options)
        self._model = config.model

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantTurn:
        request: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": DEFAULT_TEMPERATURE,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"

        try:
            response = self._client.chat.completions.create(**request)
        except Exception as exc:
            raise AgentUpstreamError() from exc

        choices = getattr(response, "choices", None)
        if not choices:
            raise AgentUpstreamError("模型服务没有返回候选结果。")
        message = choices[0].message
        calls = []
        for call in getattr(message, "tool_calls", None) or []:
            function = getattr(call, "function", None)
            if function is None:
                continue
            calls.append(
                ToolCall(
                    id=call.id,
                    name=function.name,
                    arguments=function.arguments or "{}",
                )
            )
        return AssistantTurn(content=message.content, tool_calls=tuple(calls))
