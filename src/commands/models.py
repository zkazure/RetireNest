"""命令协议的纯数据描述。

一个命令由 manifest（question、inputs、outputs、单位、约束）和一个
handler（输入 -> 输出）组成。manifest 不包含页面布局或文案。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class InputSpec:
    name: str
    question: str
    type: str
    unit: str | None = None
    required: bool = True
    default: Any = None
    options: tuple[str, ...] = ()
    constraints: Mapping[str, Any] = field(default_factory=dict)
    semantic: str | None = None
    required_when: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class OutputSpec:
    name: str
    question: str
    type: str
    unit: str | None = None
    semantic: str | None = None
    precision: int | None = None
    time_axis: Mapping[str, Any] | None = None


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


@dataclass(frozen=True, slots=True)
class Command:
    manifest: CommandManifest
    handler: Callable[[Mapping[str, Any]], Mapping[str, Any]]
