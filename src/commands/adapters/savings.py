"""储蓄增长与目标倒推命令。"""

from __future__ import annotations

from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from plan.models import FieldError
from savings import SavingsGoalInput, SavingsProjectInput, project, required_contribution
from savings.models import (
    COMPOUNDING_ANNUAL,
    COMPOUNDING_MONTHLY,
    TIMING_BEGIN,
    TIMING_END,
)

MAX_AMOUNT = 1_000_000_000
RETURN = {"min": -5, "max": 15}
INFLATION = {"min": 0, "max": 10}
COMPOUNDING = {"按年": COMPOUNDING_ANNUAL, "按月": COMPOUNDING_MONTHLY}
TIMING = {"期末": TIMING_END, "期初": TIMING_BEGIN}

COMMON_INPUTS = (
    InputSpec(
        name="current_savings",
        question="你现在有多少可用于退休规划的储蓄？",
        type="number",
        unit="元",
        description="按今天的购买力填写，不含负债；与后续现金流都用实际值。",
        constraints={"min": 0, "max": MAX_AMOUNT},
    ),
    InputSpec(
        name="annual_return_pct",
        question="你预期的名义年回报率？",
        type="number",
        unit="%",
        description="名义值，不是实际回报；工具会用 inflation_pct 折算实际回报。",
        constraints=RETURN,
    ),
    InputSpec(
        name="inflation_pct",
        question="你预期的年通胀率？",
        type="number",
        unit="%",
        description="用于把名义回报折算成实际回报；所有余额输出都按实际值。",
        constraints=INFLATION,
    ),
    InputSpec(
        name="years",
        question="计划存多少年？",
        type="integer",
        unit="年",
        description="从现在到退休（或到目标时点）的年数，整数。",
        constraints={"min": 1, "max": 60},
    ),
    InputSpec(
        name="compounding",
        question="复利频率？",
        type="enum",
        options=("按年", "按月"),
        required=False,
        default="按年",
        description="默认按年，与主页口径一致；按月适合工资按月到账的场景。",
    ),
    InputSpec(
        name="timing",
        question="投入发生在期末还是期初？",
        type="enum",
        options=("期末", "期初"),
        required=False,
        default="期末",
        description="默认期末；期初会把当年投入也多算一期收益。",
    ),
)


def _assumptions(
    compounding: str,
    timing: str,
    annual_return_pct: float,
    inflation_pct: float,
    real_return_pct: float,
) -> str:
    return (
        f"按实际购买力计算；复利频率为{compounding}，投入在{timing}；"
        f"名义年回报 {annual_return_pct:g}%，通胀 {inflation_pct:g}%，"
        f"折合实际年回报 {real_return_pct:.2f}%。月投入按实际值恒定，"
        "名义上随通胀增长；结果是基于假设的估算，不构成投资建议。"
    )


PROJECT_MANIFEST = CommandManifest(
    id="savings.project",
    version="1.0.0",
    question="每月固定投入一笔钱，按给定收益率和年限，未来能攒到多少？",
    description="按月或按年复利，输出实际余额与名义余额；月投入按实际购买力恒定。",
    when_to_use="用户已经给出每月投入，只问未来余额时用。",
    when_not_to_use=(
        "用户问每月要存多少才能达到目标时用 savings.goal；"
        "问退休后钱够不够时用 simulation.retirement。"
    ),
    inputs=(
        COMMON_INPUTS[0],
        InputSpec(
            name="monthly_contribution",
            question="你每月能拿出多少钱用于退休储蓄？",
            type="number",
            unit="元/月",
            description="按今天的购买力填写；工具会把 12 个月合计计入每年投入。",
            constraints={"min": 0, "max": MAX_AMOUNT},
        ),
        *COMMON_INPUTS[1:],
    ),
    outputs=(
        OutputSpec(
            name="future_balance_real",
            question="未来实际余额",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="future_balance_nominal",
            question="未来名义余额",
            type="number",
            unit="元",
            semantic="money_total_nominal",
            precision=0,
        ),
        OutputSpec(
            name="total_contributions_real",
            question="新增投入合计",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="total_invested_real",
            question="本金加新增投入",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="growth_real",
            question="投资增值",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="real_return_pct",
            question="实际年回报率",
            type="number",
            unit="%",
            semantic="percent",
            precision=2,
            visible=False,
        ),
        OutputSpec(name="assumptions", question="计算假设", type="text"),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {
                "current_savings": 500_000,
                "monthly_contribution": 3_000,
                "annual_return_pct": 5,
                "inflation_pct": 2,
                "years": 20,
                "compounding": "按年",
                "timing": "期末",
            },
        },
    ),
)

GOAL_MANIFEST = CommandManifest(
    id="savings.goal",
    version="1.0.0",
    question="想达到一个目标金额，每月需要存多少钱？",
    description="反推月投入；目标已被现有储蓄覆盖时返回 0，不返回负数。",
    when_to_use="用户给出目标金额，问每月需要存多少时用。",
    when_not_to_use=(
        "用户只问未来余额时用 savings.project；"
        "不要反复调用 savings.project 试参数来逼近目标。"
    ),
    inputs=(
        InputSpec(
            name="target_amount",
            question="你希望达到的目标金额？",
            type="number",
            unit="元",
            description="按今天的购买力填写，例如退休时希望拥有的实际资产。",
            constraints={"min": 0, "max": MAX_AMOUNT},
        ),
        *COMMON_INPUTS,
    ),
    outputs=(
        OutputSpec(
            name="required_monthly_contribution_real",
            question="所需月投入",
            type="number",
            unit="元/月",
            semantic="money_per_month_real",
            precision=0,
        ),
        OutputSpec(
            name="required_annual_contribution_real",
            question="所需年投入",
            type="number",
            unit="元/年",
            semantic="money_per_year_real",
            precision=0,
        ),
        OutputSpec(
            name="projected_without_contribution_real",
            question="不新增投入时的未来余额",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="shortfall_real",
            question="目标缺口",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="real_return_pct",
            question="实际年回报率",
            type="number",
            unit="%",
            semantic="percent",
            precision=2,
            visible=False,
        ),
        OutputSpec(name="assumptions", question="计算假设", type="text"),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {
                "target_amount": 2_000_000,
                "current_savings": 500_000,
                "annual_return_pct": 5,
                "inflation_pct": 2,
                "years": 20,
                "compounding": "按年",
                "timing": "期末",
            },
        },
    ),
)


def _domain_error(exc: ValueError) -> CommandInputError:
    return CommandInputError("请检查输入。", [FieldError("inputs", str(exc))])


def handle_project(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        data = SavingsProjectInput(
            current_savings=inputs["current_savings"],
            monthly_contribution=inputs["monthly_contribution"],
            annual_return_pct=inputs["annual_return_pct"],
            inflation_pct=inputs["inflation_pct"],
            years=inputs["years"],
            compounding=COMPOUNDING[str(inputs["compounding"])],
            timing=TIMING[str(inputs["timing"])],
        )
    except ValueError as exc:
        raise _domain_error(exc) from exc

    result = project(data)
    return {
        "future_balance_real": result.future_balance_real,
        "future_balance_nominal": result.future_balance_nominal,
        "total_contributions_real": result.total_contributions_real,
        "total_invested_real": result.total_invested_real,
        "growth_real": result.growth_real,
        "real_return_pct": result.real_return_pct,
        "assumptions": _assumptions(
            str(inputs["compounding"]),
            str(inputs["timing"]),
            data.annual_return_pct,
            data.inflation_pct,
            result.real_return_pct,
        ),
    }


def handle_goal(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        data = SavingsGoalInput(
            target_amount=inputs["target_amount"],
            current_savings=inputs["current_savings"],
            annual_return_pct=inputs["annual_return_pct"],
            inflation_pct=inputs["inflation_pct"],
            years=inputs["years"],
            compounding=COMPOUNDING[str(inputs["compounding"])],
            timing=TIMING[str(inputs["timing"])],
        )
    except ValueError as exc:
        raise _domain_error(exc) from exc

    result = required_contribution(data)
    return {
        "required_monthly_contribution_real": result.required_monthly_contribution_real,
        "required_annual_contribution_real": result.required_annual_contribution_real,
        "projected_without_contribution_real": result.projected_without_contribution_real,
        "shortfall_real": result.shortfall_real,
        "real_return_pct": result.real_return_pct,
        "assumptions": _assumptions(
            str(inputs["compounding"]),
            str(inputs["timing"]),
            data.annual_return_pct,
            data.inflation_pct,
            result.real_return_pct,
        ),
    }


PROJECT_COMMAND = Command(manifest=PROJECT_MANIFEST, handler=handle_project)
GOAL_COMMAND = Command(manifest=GOAL_MANIFEST, handler=handle_goal)
COMMANDS = (PROJECT_COMMAND, GOAL_COMMAND)
"""注册表使用的两个储蓄命令。"""
