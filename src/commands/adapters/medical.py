"""医疗预算命令。"""

from __future__ import annotations

from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from medical import estimate_medical_cost

MANIFEST = CommandManifest(
    id="medical.estimate",
    version="1.0.0",
    question="在当前年龄、城市和医保类型下，医疗预算大概多少？",
    description="按 2025 年参考价格估算年度和月度医疗消费；调整系数为演示假设。",
    as_of="2025",
    inputs=(
        InputSpec(
            name="age",
            question="你现在多少岁？",
            type="integer",
            unit="岁",
            constraints={"min": 0, "max": 120},
        ),
        InputSpec(
            name="city",
            question="你在哪个城市生活？",
            type="text",
            constraints={"max_length": 30},
        ),
        InputSpec(
            name="insurance",
            question="你的医保类型？",
            type="enum",
            options=("职工医保", "居民医保", "无医保"),
        ),
    ),
    outputs=(
        OutputSpec(name="age_group", question="年龄段", type="text"),
        OutputSpec(
            name="annual_medical_cost",
            question="年度医疗预算",
            type="number",
            unit="元/年",
            semantic="money_per_year_nominal",
        ),
        OutputSpec(
            name="monthly_medical_cost",
            question="月度医疗预算",
            type="number",
            unit="元/月",
            semantic="money_per_month_nominal",
        ),
        OutputSpec(name="note", question="估算说明", type="text"),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {"age": 30, "city": "广州", "insurance": "职工医保"},
        },
    ),
)
"""医疗命令的 manifest。"""


def handle(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        return estimate_medical_cost(
            age=inputs["age"],
            city=inputs["city"],
            insurance=inputs["insurance"],
        )
    except ValueError as exc:
        raise CommandInputError(str(exc)) from exc


COMMAND = Command(manifest=MANIFEST, handler=handle)
"""注册表使用的命令对象。"""
