"""退休规划聚合命令。

这是主页唯一负责“退休资金”结论的命令：目标、预计资产、缺口、资产轨迹与
三情景都从这里返回。医疗、养老、存款、生活支出由各自的命令独立测算，
不并入这里的目标与缺口。
"""

from __future__ import annotations

from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from plan import (
    PlanInput,
    build_explanation,
    build_scenarios,
    calculate,
    input_payload,
    scenario_payload,
    validate,
)

WARNINGS = (
    "医疗、养老、存款与生活支出为独立命令的测算结果，不并入这里的退休资金目标。",
    "结果基于你填写的假设，不构成投资建议。",
)
"""主页解读区使用的提醒；与 `/api/retirement/plan` 的提醒各自独立。"""


MANIFEST = CommandManifest(
    id="plan.retirement",
    version="1.0.0",
    question="按现在的收入和支出，退休时能攒下多少、还差多少？",
    description="根据年龄、收支、资产与假设，测算退休资金目标、预计资产、缺口与三情景。",
    inputs=(
        # 与 living.calculate 共用的字段沿用同一套问法，避免同一语义出现两种措辞。
        InputSpec(
            name="age",
            question="你现在多少岁？",
            type="integer",
            unit="岁",
            constraints={"min": 18, "max": 80},
        ),
        InputSpec(
            name="city",
            question="你现在居住的城市？",
            type="text",
            constraints={"max_length": 30},
        ),
        InputSpec(
            name="retire_age",
            question="期望退休年龄？",
            type="integer",
            unit="岁",
            constraints={"min": 18, "max": 85},
        ),
        InputSpec(
            name="life_expectancy",
            question="规划至年龄？",
            type="integer",
            unit="岁",
            constraints={"min": 18, "max": 110},
        ),
        InputSpec(
            name="monthly_income",
            question="你现在每月的税后收入？",
            type="number",
            unit="元/月",
            constraints={"min": 0, "max": 1_000_000_000},
        ),
        InputSpec(
            name="monthly_expense",
            question="当前每月总支出（含通勤、正装、外卖）？",
            type="number",
            unit="元/月",
            constraints={"min": 0.01, "max": 1_000_000_000},
        ),
        InputSpec(
            name="assets",
            question="你现在一共有多少资产？",
            type="number",
            unit="元",
            constraints={"min": 0, "max": 1_000_000_000},
        ),
        InputSpec(
            name="debt",
            question="你现在有多少负债？",
            type="number",
            unit="元",
            constraints={"min": 0, "max": 1_000_000_000},
        ),
        InputSpec(
            name="retirement_expense",
            question="退休后每月打算花多少？",
            type="number",
            unit="元/月",
            constraints={"min": 0, "max": 1_000_000_000},
        ),
        InputSpec(
            name="monthly_pension",
            question="你预计每月能领多少养老金？",
            type="number",
            unit="元/月",
            constraints={"min": 0, "max": 1_000_000_000},
        ),
        InputSpec(
            name="nominal_return",
            question="你预期的名义年回报率？",
            type="number",
            unit="%",
            constraints={"min": -5, "max": 15},
        ),
        InputSpec(
            name="inflation",
            question="你预期的年通胀率？",
            type="number",
            unit="%",
            constraints={"min": 0, "max": 10},
        ),
    ),
    outputs=(
        OutputSpec(
            name="target",
            question="退休所需资金",
            type="number",
            unit="元",
            semantic="money_target_real",
            precision=0,
        ),
        OutputSpec(
            name="projected",
            question="退休时预计资产",
            type="number",
            unit="元",
            semantic="money_projected_real",
            precision=0,
        ),
        OutputSpec(
            name="gap",
            question="资金缺口",
            type="number",
            unit="元",
            semantic="money_gap_real",
            precision=0,
        ),
        OutputSpec(
            name="coverage",
            question="目标准备度",
            type="number",
            unit="%",
            semantic="ratio",
            precision=1,
        ),
        OutputSpec(
            name="required_monthly_saving",
            question="覆盖目标所需月结余",
            type="number",
            unit="元/月",
            semantic="money_per_month_real",
            precision=0,
        ),
        OutputSpec(
            name="monthly_surplus",
            question="当前月结余",
            type="number",
            unit="元/月",
            semantic="money_per_month_real",
            precision=0,
        ),
        OutputSpec(
            name="years_to_retirement",
            question="距离退休还有几年",
            type="integer",
            unit="年",
            visible=False,
        ),
        OutputSpec(
            name="retirement_years",
            question="退休后规划年数",
            type="integer",
            unit="年",
            visible=False,
        ),
        OutputSpec(
            name="real_return",
            question="实际年回报率",
            type="number",
            semantic="ratio",
            visible=False,
        ),
        OutputSpec(
            name="depleted_age",
            question="资产不足的年龄",
            type="integer",
            unit="岁",
            visible=False,
        ),
        OutputSpec(
            name="points",
            question="逐年资产轨迹",
            type="object",
            semantic="money_per_year_real",
            time_axis={"start": "age", "step_years": 1},
            visible=False,
        ),
        OutputSpec(name="scenarios", question="三情景对比", type="object", visible=False),
        OutputSpec(name="explanation", question="规划解读", type="text", visible=False),
        OutputSpec(name="warnings", question="提醒", type="object", visible=False),
        OutputSpec(name="plan_input", question="本次使用的输入", type="object", visible=False),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {
                "city": "珠海",
                "age": 30,
                "retire_age": 55,
                "life_expectancy": 90,
                "monthly_income": 20000,
                "monthly_expense": 12000,
                "assets": 500000,
                "debt": 0,
                "retirement_expense": 8000,
                "monthly_pension": 3000,
                "nominal_return": 5,
                "inflation": 2,
            },
        },
    ),
)
"""退休规划命令的 manifest。"""


def handle(inputs: dict[str, Any]) -> dict[str, Any]:
    plan_input = PlanInput(
        city=inputs["city"],
        age=inputs["age"],
        retirement_age=inputs["retire_age"],
        life_expectancy=inputs["life_expectancy"],
        monthly_income=inputs["monthly_income"],
        monthly_expense=inputs["monthly_expense"],
        assets=inputs["assets"],
        debt=inputs["debt"],
        retirement_expense=inputs["retirement_expense"],
        monthly_pension=inputs["monthly_pension"],
        nominal_return=inputs["nominal_return"],
        inflation=inputs["inflation"],
    )
    errors = validate(plan_input)
    if errors:
        raise CommandInputError("请检查输入。", errors)

    result = calculate(plan_input)
    scenarios = build_scenarios(plan_input)
    return {
        "target": result.target,
        "projected": result.projected,
        "gap": result.gap,
        "coverage": result.coverage,
        "required_monthly_saving": result.required_monthly_saving,
        "monthly_surplus": result.monthly_surplus,
        "years_to_retirement": result.years_to_retirement,
        "retirement_years": result.retirement_years,
        "real_return": result.real_return,
        "depleted_age": result.depleted_age,
        "points": [{"age": point.age, "assets": point.assets} for point in result.points],
        "scenarios": [scenario_payload(scenario) for scenario in scenarios],
        "explanation": build_explanation(plan_input, result),
        "warnings": list(WARNINGS),
        "plan_input": input_payload(plan_input),
    }


COMMAND = Command(manifest=MANIFEST, handler=handle)
"""注册表使用的命令对象。"""
