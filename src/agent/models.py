"""Agent 层的数据结构。

工具目录由命令 manifest 生成；会话与循环只处理 OpenAI 兼容的消息字典，
避免把 provider 的响应对象漏进业务代码。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ToolCall:
    """模型请求的一次工具调用；arguments 保留原始 JSON 字符串。"""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class AssistantTurn:
    """模型的一次回复：文本与（可选的）工具调用。"""

    content: str | None
    tool_calls: tuple[ToolCall, ...] = ()


class ChatClient(Protocol):
    """模型客户端接口；测试用脚本化假模型实现同一协议。"""

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantTurn: ...


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """一个命令生成的工具定义。"""

    name: str
    command_id: str
    version: str
    description: str
    parameters: Mapping[str, Any]
    when_to_use: str = ""

    def as_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": dict(self.parameters),
            },
        }


@dataclass(frozen=True, slots=True)
class ToolCatalog:
    """工具清单及其按名称/命令 ID 的索引。"""

    specs: tuple[ToolSpec, ...]

    @property
    def by_name(self) -> dict[str, ToolSpec]:
        return {spec.name: spec for spec in self.specs}

    @property
    def by_command_id(self) -> dict[str, ToolSpec]:
        return {spec.command_id: spec for spec in self.specs}

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [spec.as_openai_tool() for spec in self.specs]

    def prompt_section(self) -> str:
        lines = []
        for spec in self.specs:
            hint = spec.when_to_use or spec.description.splitlines()[0]
            lines.append(f"- {spec.name}（{spec.command_id}）：{hint}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class AgentRun:
    """一次循环的结果；tool_calls 是完整的调用轨迹。"""

    reply: str
    tool_calls: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AgentReply:
    """对外返回的对话结果。"""

    session_id: str
    reply: str
    tool_calls: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]
    model: str
