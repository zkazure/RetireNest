"""通胀换算命令。"""

from __future__ import annotations

from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from inflation import NOMINAL_TO_REAL, REAL_TO_NOMINAL, InflationInput, convert
from plan.models import FieldError

MAX_AMOUNT = 1_000_000_000
DIRECTIONS = {"名义转实际": NOMINAL_TO_REAL, "实际转名义": REAL_TO_NOMINAL}

MANIFEST = CommandManifest(
    id="inflation.convert",
    version="1.0.0",
    question="一笔名义金额，相当于今天多少购买力？或者反过来？",
    description="按年复利折算名义金额与实际购买力；方向只决定乘除。",
    when_to_use="用户给了一个名义金额，问相当于今天多少钱，或反向换算时用。",
    when_not_to_use=(
        "不要用它调整 savings.* 或 simulation.* 的输出：那些工具已经按实际购买力计算，"
        "再套一次会重复扣通胀。"
    ),
    inputs=(
        InputSpec(
            name="amount",
            question="要换算的金额？",
            type="number",
            unit="元",
            description="按输入方向的含义填写；正值，最多 10 亿元。",
            constraints={"min": 0, "max": MAX_AMOUNT},
        ),
        InputSpec(
            name="annual_inflation_pct",
            question="你预期的年通胀率？",
            type="number",
            unit="%",
            description="年复利通胀率，用于计算累计系数。",
            constraints={"min": 0, "max": 10},
        ),
        InputSpec(
            name="years",
            question="经过多少年？",
            type="integer",
            unit="年",
            description="从今天到目标时点的年数；0 表示不折算。",
            constraints={"min": 0, "max": 60},
        ),
        InputSpec(
            name="direction",
            question="换算方向？",
            type="enum",
            options=("名义转实际", "实际转名义"),
            required=False,
            default="名义转实际",
            description="默认把名义金额折成今天购买力；反向用于把今天的钱折成未来名义值。",
        ),
    ),
    outputs=(
        OutputSpec(
            name="converted_amount",
            question="换算后的金额",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=2,
        ),
        OutputSpec(
            name="cumulative_factor",
            question="累计通胀系数",
            type="number",
            unit="倍",
            precision=6,
        ),
        OutputSpec(
            name="annual_inflation_pct",
            question="使用的年通胀率",
            type="number",
            unit="%",
            semantic="percent",
            precision=2,
        ),
        OutputSpec(name="direction", question="换算方向", type="text"),
        OutputSpec(name="note", question="使用提示", type="text"),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {
                "amount": 1_000_000,
                "annual_inflation_pct": 2,
                "years": 20,
                "direction": "名义转实际",
            },
        },
    ),
)


def handle(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        data = InflationInput(
            amount=inputs["amount"],
            annual_inflation_pct=inputs["annual_inflation_pct"],
            years=inputs["years"],
            direction=DIRECTIONS[str(inputs["direction"])],
        )
    except ValueError as exc:
        raise CommandInputError("请检查输入。", [FieldError("inputs", str(exc))]) from exc

    result = convert(data)
    return {
        "converted_amount": result.converted_amount,
        "cumulative_factor": result.cumulative_factor,
        "annual_inflation_pct": result.annual_inflation_pct,
        "direction": str(inputs["direction"]),
        "note": (
            "savings.* 与 simulation.* 已按实际购买力计算，"
            "不要再用本工具重复折算它们的输出。"
        ),
    }


COMMAND = Command(manifest=MANIFEST, handler=handle)
