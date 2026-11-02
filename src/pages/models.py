"""页面清单的纯数据描述。

页面清单只描述“有哪些字段、怎么分组、提交时调用哪些命令”，不携带任何
问题文案：字段的 question、类型、单位、选项与约束都在命令 manifest 里，
由 `resolve.py` 解析时取用。

字段的 `command` 是文案与控件的来源命令；执行清单决定这个字段最终交给
哪些命令。两者可以是不同命令（例如城市用生活支出的枚举渲染，同时提交给
退休规划与医疗预算）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


class PageError(Exception):
    """页面定义不合法；只在开发期暴露，生产环境应视为服务端配置错误。"""


@dataclass(frozen=True, slots=True)
class PageField:
    name: str
    command: str
    """提供 question、类型、选项与约束的命令。"""
    input: str | None = None
    """该命令的输入名；省略时与字段名相同。"""
    hint: str | None = None
    visible_when: tuple[Mapping[str, Any], ...] = ()

    @property
    def source_input(self) -> str:
        return self.input or self.name


@dataclass(frozen=True, slots=True)
class PageToggle:
    name: str
    label: str
    default: bool = False


@dataclass(frozen=True, slots=True)
class PageSection:
    id: str
    title: str
    fields: tuple[PageField, ...]
    description: str | None = None
    toggle: PageToggle | None = None


@dataclass(frozen=True, slots=True)
class PageExecution:
    """一次命令调用：把页面字段映射成命令参数。"""

    command: str
    inputs: Mapping[str, str]
    toggle: str | None = None
    """只有对应开关打开时才执行；None 表示总是执行。"""


@dataclass(frozen=True, slots=True)
class PageRule:
    type: str
    left: str
    right: str
    message: str
    minimum: float | None = None


@dataclass(frozen=True, slots=True)
class PageManifest:
    id: str
    version: str
    title: str
    description: str
    sections: tuple[PageSection, ...]
    executions: tuple[PageExecution, ...]
    rules: tuple[PageRule, ...] = field(default=())

    def fields(self) -> tuple[PageField, ...]:
        return tuple(field for section in self.sections for field in section.fields)

    def toggles(self) -> tuple[PageToggle, ...]:
        return tuple(section.toggle for section in self.sections if section.toggle is not None)
