"""活期存款收益命令。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from deposit import SNAPSHOT, DemandDeposit, DepositError, calculate


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


AS_OF = SNAPSHOT[0].fetched_at.isoformat()
"""默认利率快照的抓取日期。"""


MANIFEST = CommandManifest(
    id="deposit.demand",
    version="1.0.0",
    question="一笔活期存款到期能拿多少利息？",
    description="单利一次性计息，年利率按 360 天折算，天数算头不算尾。",
    as_of=AS_OF,
    inputs=(
        InputSpec(
            name="principal",
            question="存款本金？",
            type="decimal",
            unit="元",
            constraints={"min": 0.01, "precision": 2},
        ),
        InputSpec(name="start_date", question="存款开始日期？", type="date"),
        InputSpec(name="end_date", question="存款结束日期？", type="date"),
        InputSpec(
            name="annual_rate",
            question="年利率（可选，小数比例，例如 0.0005）？",
            type="decimal",
            required=False,
            constraints={"min": 0, "max": 1, "precision": 8},
        ),
    ),
    outputs=(
        OutputSpec(name="principal", question="本金", type="decimal", unit="元"),
        OutputSpec(
            name="annual_rate",
            question="本次使用的年利率",
            type="decimal",
            semantic="ratio",
        ),
        OutputSpec(name="days", question="计息天数", type="integer", unit="天"),
        OutputSpec(
            name="interest",
            question="利息",
            type="decimal",
            unit="元",
            semantic="money_total_nominal",
        ),
        OutputSpec(
            name="total",
            question="期末本息",
            type="decimal",
            unit="元",
            semantic="money_total_nominal",
        ),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {
                "principal": "100000.20",
                "annual_rate": "0.0005",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
            },
        },
    ),
)
"""存款命令的 manifest。"""


def handle(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = calculate(
            DemandDeposit(
                principal=inputs["principal"],
                start_date=inputs["start_date"],
                end_date=inputs["end_date"],
                annual_rate=inputs.get("annual_rate"),
            )
        )
    except DepositError as exc:
        raise CommandInputError(str(exc)) from exc

    return {
        "principal": _decimal_text(result.principal),
        "annual_rate": _decimal_text(result.annual_rate),
        "days": result.days,
        "interest": _decimal_text(result.interest),
        "total": _decimal_text(result.total),
    }


COMMAND = Command(manifest=MANIFEST, handler=handle)
"""注册表使用的命令对象。"""
