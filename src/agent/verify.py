"""数字一致性提示。

模型可能在回复里编造或改写金额。这里只做启发式检查：抽取回复中带 元/万/亿
的金额，与工具输入/输出里的数值比对；对不上时追加 warning，不改写回复。
百分比与年龄不检查，避免把“4% 法则”“55 岁”误判成金额。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")
_WITH_YUAN = re.compile(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)\s*(万|亿)?\s*元")
_WITH_UNIT = re.compile(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)\s*(万|亿)(?!\s*(?:年|岁|%|％))")
_UNIT_SCALE = {"万": 10_000.0, "亿": 100_000_000.0}
_RELATIVE_TOLERANCE = 0.02
_ABSOLUTE_TOLERANCE = 0.5


def _amounts(text: str) -> list[float]:
    found: list[tuple[int, float]] = []
    for pattern in (_WITH_YUAN, _WITH_UNIT):
        for match in pattern.finditer(text):
            number = float(match.group(1).replace(",", ""))
            scale = _UNIT_SCALE.get(match.group(2) or "", 1.0)
            found.append((match.start(), number * scale))
    unique: list[float] = []
    seen_starts: set[int] = set()
    for start, value in found:
        if start in seen_starts:
            continue
        seen_starts.add(start)
        if not any(_close(value, existing) for existing in unique):
            unique.append(value)
    return unique


def _collect_numbers(value: Any, out: list[float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        out.append(float(value))
        return
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if _NUMBER.fullmatch(cleaned):
            out.append(float(cleaned))
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _collect_numbers(item, out)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _collect_numbers(item, out)


def _close(left: float, right: float) -> bool:
    tolerance = max(_ABSOLUTE_TOLERANCE, abs(right) * _RELATIVE_TOLERANCE)
    return abs(left - right) <= tolerance


def _format(value: float) -> str:
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.2f} 亿"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.2f} 万"
    return f"{value:,.0f} 元"


def numeric_warnings(
    reply: str,
    tool_calls: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> list[str]:
    """返回金额对不上的提示；空列表表示没有发现问题。"""
    amounts = _amounts(reply)
    if not amounts:
        return []

    allowed: list[float] = []
    for record in tool_calls:
        _collect_numbers(record.get("inputs"), allowed)
        _collect_numbers(record.get("outputs"), allowed)

    unmatched: list[float] = []
    for amount in amounts:
        if any(_close(amount, candidate) for candidate in allowed):
            continue
        if any(_close(amount, existing) for existing in unmatched):
            continue
        unmatched.append(amount)

    if not unmatched:
        return []
    sample = "、".join(_format(value) for value in unmatched[:3])
    return [
        f"回复中的金额 {sample} 没有对应的工具输入或输出，请以工具结果为准。",
    ]
