"""养老金命令。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from pension import BasicPensionInput, PensionError, calculate


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


MANIFEST = CommandManifest(
    id="pension.basic",
    version="1.0.0",
    question="退休当月能领多少城镇职工基本养老金？",
    description="按法定退休年龄、缴费年限、平均缴费指数和个人账户余额测算。",
    as_of="2025",
    inputs=(
        InputSpec(name="birth_date", question="你的出生日期？", type="date"),
        InputSpec(
            name="gender",
            question="性别？",
            type="enum",
            options=("男", "女"),
        ),
        InputSpec(
            name="category",
            question="岗位类别（女性必填）？",
            type="enum",
            options=("管理技术", "工人"),
            required=False,
            required_when={"field": "gender", "equals": "女"},
        ),
        InputSpec(
            name="contribution_years",
            question="累计缴费年限？",
            type="decimal",
            unit="年",
            constraints={"min": 0.01, "max": 50, "precision": 2},
        ),
        InputSpec(
            name="average_index",
            question="平均缴费指数？",
            type="decimal",
            constraints={"min": 0.6, "max": 3, "precision": 4},
        ),
        InputSpec(
            name="account_balance",
            question="退休时个人账户余额？",
            type="decimal",
            unit="元",
            constraints={"min": 0, "precision": 2},
        ),
        InputSpec(
            name="calculation_base",
            question="月养老金计发基数？",
            type="decimal",
            unit="元/月",
            constraints={"min": 0.01, "precision": 2},
        ),
        InputSpec(
            name="prior_monthly_wage",
            question="退休前月工资（可选，用于替代率）？",
            type="decimal",
            unit="元",
            required=False,
            constraints={"min": 0.01, "precision": 2},
        ),
        InputSpec(
            name="annual_adjustment",
            question="养老金年调整率（可选，小数比例）？",
            type="decimal",
            required=False,
            constraints={"min": 0, "max": 1, "precision": 6},
        ),
    ),
    outputs=(
        OutputSpec(
            name="retirement_age_months",
            question="法定退休年龄",
            type="integer",
            unit="月",
        ),
        OutputSpec(name="payout_months", question="计发月数", type="integer", unit="月"),
        OutputSpec(
            name="basic_pension",
            question="基础养老金",
            type="decimal",
            unit="元/月",
            semantic="money_per_month_nominal",
        ),
        OutputSpec(
            name="account_pension",
            question="个人账户养老金",
            type="decimal",
            unit="元/月",
            semantic="money_per_month_nominal",
        ),
        OutputSpec(
            name="total",
            question="合计月养老金",
            type="decimal",
            unit="元/月",
            semantic="money_per_month_nominal",
        ),
        OutputSpec(
            name="annual_adjustment",
            question="后续年度名义调整率",
            type="decimal",
            semantic="ratio",
        ),
        OutputSpec(
            name="replacement_rate",
            question="替代率（无退休前工资时为 null）",
            type="decimal",
            semantic="ratio",
        ),
        OutputSpec(
            name="calculation_base",
            question="本次使用的计发基数",
            type="decimal",
            unit="元/月",
        ),
        OutputSpec(name="average_index", question="本次使用的平均缴费指数", type="decimal"),
        OutputSpec(
            name="contribution_years",
            question="本次使用的缴费年限",
            type="decimal",
            unit="年",
        ),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {
                "birth_date": "1965-06-01",
                "gender": "男",
                "contribution_years": "30.0",
                "average_index": "1.0",
                "account_balance": "150000.00",
                "calculation_base": "8000.00",
            },
        },
    ),
)
"""养老金命令的 manifest。"""


def handle(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = calculate(
            BasicPensionInput(
                birth_date=inputs["birth_date"],
                gender=inputs["gender"],
                category=inputs.get("category"),
                contribution_years=inputs["contribution_years"],
                average_index=inputs["average_index"],
                account_balance=inputs["account_balance"],
                calculation_base=inputs["calculation_base"],
                prior_monthly_wage=inputs.get("prior_monthly_wage"),
                annual_adjustment=inputs.get("annual_adjustment"),
            )
        )
    except PensionError as exc:
        raise CommandInputError(str(exc)) from exc

    return {
        "retirement_age_months": result.retirement_age_months,
        "payout_months": result.payout_months,
        "basic_pension": _decimal_text(result.basic_pension),
        "account_pension": _decimal_text(result.account_pension),
        "total": _decimal_text(result.total),
        "annual_adjustment": _decimal_text(result.annual_adjustment),
        "replacement_rate": _decimal_text(result.replacement_rate),
        "calculation_base": _decimal_text(result.calculation_base),
        "average_index": _decimal_text(result.average_index),
        "contribution_years": _decimal_text(result.contribution_years),
    }


COMMAND = Command(manifest=MANIFEST, handler=handle)
"""注册表使用的命令对象。"""
