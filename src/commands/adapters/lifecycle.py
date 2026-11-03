"""全周期仿真与策略对比命令。"""

from __future__ import annotations

from profile import Profile, ProfileError, build_profile
from profile import tiers as profile_tiers
from typing import Any

from commands import tiers as tier_help
from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from lifecycle import compare, project, simulate
from living.constants import CITY_TIER
from strategy import StrategyError

CITIES = tuple(CITY_TIER)


def _profile_inputs(extra: tuple[InputSpec, ...] = ()) -> tuple[InputSpec, ...]:
    return (
        InputSpec(name="age", question="你现在多少岁？", type="integer", unit="岁",
                  required=False, constraints={"min": 18, "max": 100}),
        InputSpec(name="sex", question="性别？", type="enum", options=("男", "女")),
        InputSpec(name="city", question="你现在居住的城市？", type="enum", options=CITIES),
        InputSpec(name="birth_date", question="你的出生日期？", type="date"),
        InputSpec(name="category", question="女性岗位类别（管理技术或工人）？", type="enum",
                  options=("管理技术", "工人"), required=False),
        InputSpec(name="income", question="你现在每月的税后收入？", type="tier", unit="元/月",
                  allow_custom=True, constraints={"min": 0, "max": 10_000_000},
                  tiers=tier_help.options(profile_tiers.INCOME)),
        InputSpec(name="expense", question="当前每月总支出？", type="tier", unit="元/月",
                  allow_custom=True, constraints={"min": 0, "max": 1_000_000},
                  tiers=tier_help.options(profile_tiers.EXPENSE)),
        InputSpec(name="assets", question="你现在一共有多少资产？", type="tier", unit="元",
                  allow_custom=True, constraints={"min": 0, "max": 100_000_000_000},
                  tiers=tier_help.options(profile_tiers.ASSETS)),
        InputSpec(name="debt", question="你现在有多少负债？", type="tier", unit="元",
                  allow_custom=True, constraints={"min": 0, "max": 100_000_000_000},
                  tiers=tier_help.options(profile_tiers.DEBT)),
        InputSpec(name="retirement_expense", question="退休后每月打算花多少？", type="tier",
                  unit="元/月", required=False,
                  description="可选；留空则按当前每月支出计算。",
                  allow_custom=True, constraints={"min": 0, "max": 1_000_000},
                  tiers=tier_help.options(profile_tiers.RETIRE_EXPENSE)),
        InputSpec(name="retirement_age", question="打算多少岁退休？", type="tier", unit="岁",
                  required=False, allow_custom=True,
                  constraints={"min": 30, "max": 90, "integer": True},
                  tiers=tier_help.options(profile_tiers.RETIRE_AGE)),
        InputSpec(name="travel", question="退休后每年出游几次？", type="tier",
                  allow_custom=True, constraints={"min": 0, "max": 50, "integer": True},
                  tiers=tier_help.options(profile_tiers.TRAVEL)),
        InputSpec(name="entertainment", question="娱乐开销？", type="tier",
                  allow_custom=True, constraints={"min": 0, "max": 100_000},
                  tiers=tier_help.options(profile_tiers.ENTERTAINMENT)),
        InputSpec(name="children", question="育儿计划？", type="tier",
                  allow_custom=True, constraints={"min": 0, "max": 10, "integer": True},
                  tiers=tier_help.options(profile_tiers.CHILDREN)),
        *extra,
    )


def _build(inputs: dict[str, Any]) -> Profile:
    retirement_age = None
    tier = inputs.get("retirement_age")
    if tier is not None:
        retirement_age = int(profile_tiers.amount_of(profile_tiers.RETIRE_AGE, tier))
    return build_profile(
        age=inputs.get("age"),
        sex=inputs["sex"],
        city=inputs["city"],
        birth_date=inputs["birth_date"],
        category=inputs.get("category"),
        retirement_age=retirement_age,
        income_tier=inputs["income"],
        expense_tier=inputs["expense"],
        asset_tier=inputs["assets"],
        debt_tier=inputs["debt"],
        retirement_expense_tier=inputs.get("retirement_expense"),
        travel_tier=inputs["travel"],
        entertainment_tier=inputs["entertainment"],
        children_tier=inputs["children"],
    )


_BASE_OUTPUTS = (
    OutputSpec(name="pension_monthly", question="退休后每月养老金", type="number",
               unit="元", semantic="money_flow_nominal"),
    OutputSpec(name="break_even_age", question="结余转负的年龄", type="integer",
               unit="岁", visible=False),
    OutputSpec(name="depleted_age", question="资产不足的年龄", type="integer",
               unit="岁", visible=False),
    OutputSpec(name="final_assets", question="规划终点资产", type="number",
               unit="元", semantic="money_total_nominal"),
)


PROJECT = Command(
    manifest=CommandManifest(
        id="lifecycle.project",
        version="1.0.0",
        question="按现在的收支，一辈子能不能撑住？",
        description="工作期收工资、退休期收养老金加资产收益，逐年滚动资产，给出结余转负与资产不足的年龄。",
        when_to_use="用户想要一条确定的年度现金流与资产轨迹时用。",
        when_not_to_use="用户想看概率与破产年龄分布时用 lifecycle.simulate。",
        inputs=_profile_inputs(),
        outputs=(
            *_BASE_OUTPUTS,
            OutputSpec(name="peak_assets", question="资产峰值", type="number", unit="元",
                       semantic="money_total_nominal", visible=False),
            OutputSpec(name="rows", question="逐年现金流", type="object",
                       semantic="money_per_year_nominal", time_axis={"start": "age", "step_years": 1},
                       visible=False),
        ),
    ),
    handler=lambda inputs: _project(inputs),
)


def _project(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = project(_build(inputs))
    except (ProfileError, ValueError) as exc:
        raise CommandInputError(str(exc)) from exc
    return {
        "pension_monthly": result.pension_monthly,
        "break_even_age": result.break_even_age,
        "depleted_age": result.depleted_age,
        "final_assets": result.final_assets,
        "peak_assets": result.peak_assets,
        "rows": [
            {
                "age": row.age,
                "phase": row.phase,
                "income": row.income,
                "expense": row.expense,
                "medical": row.medical,
                "soft": row.soft,
                "assets": row.assets,
            }
            for row in result.rows
        ],
    }


SIMULATE = Command(
    manifest=CommandManifest(
        id="lifecycle.simulate",
        version="1.0.0",
        question="按三档资产配置，成功概率有多大？",
        description="按配比抽收益路径，输出成功率、破产年龄分位、期末资产分位与可支撑的退休支出。",
        deterministic=True,
        when_to_use="用户问「概率」「风险」「够不够稳」时用。",
        when_not_to_use="用户只想要一条确定路径时用 lifecycle.project。",
        inputs=_profile_inputs(
            (
                InputSpec(name="paths", question="模拟路径数？", type="integer",
                          required=False, default=1000, constraints={"min": 100, "max": 20000}),
                InputSpec(name="seed", question="随机种子？", type="integer",
                          required=False, default=42, constraints={"min": 0, "max": 2**31 - 1}),
            )
        ),
        outputs=(
            *_BASE_OUTPUTS,
            OutputSpec(name="success_rate", question="成功率", type="number", semantic="ratio"),
            OutputSpec(name="depleted_p10", question="破产年龄 10% 分位", type="integer",
                       unit="岁", visible=False),
            OutputSpec(name="depleted_median", question="破产年龄中位数", type="integer",
                       unit="岁", visible=False),
            OutputSpec(name="depleted_p90", question="破产年龄 90% 分位", type="integer",
                       unit="岁", visible=False),
            OutputSpec(name="terminal_p10", question="期末资产 10% 分位", type="number",
                       unit="元", visible=False),
            OutputSpec(name="terminal_median", question="期末资产中位数", type="number",
                       unit="元", visible=False),
            OutputSpec(name="terminal_p90", question="期末资产 90% 分位", type="number",
                       unit="元", visible=False),
            OutputSpec(name="affordable_monthly_expense", question="可支撑的退休月支出",
                       type="number", unit="元", semantic="money_flow_nominal"),
        ),
    ),
    handler=lambda inputs: _simulate(inputs),
)


def _simulate(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = _build(inputs)
        projection = project(profile)
        result = simulate(
            profile,
            paths=inputs.get("paths", 1000),
            seed=inputs.get("seed", 42),
        )
    except (ProfileError, ValueError) as exc:
        raise CommandInputError(str(exc)) from exc
    return {
        "pension_monthly": projection.pension_monthly,
        "break_even_age": projection.break_even_age,
        "depleted_age": projection.depleted_age,
        "final_assets": projection.final_assets,
        "success_rate": result.success_rate,
        "depleted_p10": result.depleted_p10,
        "depleted_median": result.depleted_median,
        "depleted_p90": result.depleted_p90,
        "terminal_p10": result.terminal_p10,
        "terminal_median": result.terminal_median,
        "terminal_p90": result.terminal_p90,
        "affordable_monthly_expense": result.affordable_monthly_expense,
    }


COMPARE = Command(
    manifest=CommandManifest(
        id="strategy.compare",
        version="1.0.0",
        question="换一种活法，结果差多少？",
        description="把五个预设策略套在同一份画像上，并排给出退休年龄、养老金、破产年龄与成功率。",
        when_to_use="用户问「丁克会怎样」「提前退休行不行」这类策略对比时用。",
        inputs=_profile_inputs(),
        outputs=(
            OutputSpec(name="variants", question="策略对比", type="object"),
        ),
    ),
    handler=lambda inputs: _compare(inputs),
)


def _compare(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        summaries = compare(_build(inputs))
    except (ProfileError, StrategyError, ValueError) as exc:
        raise CommandInputError(str(exc)) from exc
    return {
        "variants": [
            {
                "preset_id": item.preset_id,
                "label": item.label,
                "retirement_age": item.retirement_age,
                "pension_monthly": item.pension_monthly,
                "break_even_age": item.break_even_age,
                "depleted_age": item.depleted_age,
                "final_assets": item.final_assets,
                "success_rate": item.success_rate,
                "affordable_monthly_expense": item.affordable_monthly_expense,
            }
            for item in summaries
        ]
    }


COMMANDS = (PROJECT, SIMULATE, COMPARE)
