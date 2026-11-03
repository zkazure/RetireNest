"""命令协议的纯数据描述。

一个命令由 manifest（question、inputs、outputs、单位、约束）和一个
handler（输入 -> 输出）组成。manifest 不包含页面布局或文案。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class TierOption:
    """选择题的一个选项：提交值、界面文案与对应的计算取值。

    `type="tier"` 的输入用它渲染分段控件，并把「按 1.75 万计算」这类回显
    一并下发给前端，避免档位映射只存在于后端。
    """

    value: str
    label: str
    amount: float


@dataclass(frozen=True, slots=True)
class InputSpec:
    name: str
    question: str
    type: str
    unit: str | None = None
    required: bool = True
    default: Any = None
    options: tuple[str, ...] = ()
    tiers: tuple[TierOption, ...] = ()
    allow_custom: bool = False
    """`type="tier"` 时是否接受档位之外的数值字符串；默认只认档位。"""
    constraints: Mapping[str, Any] = field(default_factory=dict)
    semantic: str | None = None
    required_when: Mapping[str, Any] | None = None
    # 给 LLM 看的参数说明：单位、口径、与其它参数的关系；页面不展示。
    description: str | None = None


@dataclass(frozen=True, slots=True)
class OutputSpec:
    name: str
    question: str
    type: str
    unit: str | None = None
    semantic: str | None = None
    precision: int | None = None
    time_axis: Mapping[str, Any] | None = None
    # False 表示这是实现细节（数组下标、回显输入），页面不展示。
    visible: bool = True
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CommandManifest:
    id: str
    version: str
    question: str
    inputs: tuple[InputSpec, ...]
    outputs: tuple[OutputSpec, ...]
    description: str = ""
    deterministic: bool = True
    as_of: str | None = None
    examples: tuple[Mapping[str, Any], ...] = ()
    # 工具选择指引；阶段十九生成 LLM 工具 schema 时使用，页面不展示。
    when_to_use: str = ""
    when_not_to_use: str = ""


@dataclass(frozen=True, slots=True)
class Command:
    manifest: CommandManifest
    handler: Callable[[Mapping[str, Any]], Mapping[str, Any]]
