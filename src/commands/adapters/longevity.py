"""Gompertz 寿命估计命令。"""

from __future__ import annotations

from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from longevity import AS_OF, SOURCE_NOTE, LongevityInput, estimate
from longevity.params import DISPERSION_B
from plan.models import FieldError

MANIFEST = CommandManifest(
    id="longevity.estimate",
    version="1.0.0",
    question="按年龄、性别和健康状况，大概能活到多少岁？",
    description=(
        "条件于当前年龄，用校准的 Gompertz 生存模型给出死亡年龄分位与"
        "活到 85/90/95 岁的概率；演示参数，不是医学预测。"
    ),
    deterministic=True,
    as_of=AS_OF,
    when_to_use=(
        "用户问预期寿命、长寿风险，或需要为退休规划选一个规划终点时用。"
    ),
    when_not_to_use=(
        "不要把它当成个体医学预测；也不要直接拿中位数替换用户明确给出的"
        "规划终点，先说明中位数与分位数的区别。"
    ),
    inputs=(
        InputSpec(
            name="current_age",
            question="你现在多少岁？",
            type="integer",
            unit="岁",
            description="周岁，整数；结果条件于已经活到这个年龄。",
            constraints={"min": 18, "max": 100},
        ),
        InputSpec(
            name="sex",
            question="你的性别？",
            type="enum",
            options=("男", "女"),
            description="用于选择基准预期寿命。",
        ),
        InputSpec(
            name="health",
            question="你目前的健康状况？",
            type="enum",
            options=("较差", "一般", "良好"),
            required=False,
            default="一般",
            description="演示档位：较差/一般/良好分别把基准寿命平移 -4/0/+3 年。",
        ),
    ),
    outputs=(
        OutputSpec(
            name="median_age_at_death",
            question="死亡年龄中位数",
            type="number",
            unit="岁",
            semantic="age",
            precision=1,
        ),
        OutputSpec(
            name="p10_age_at_death",
            question="死亡年龄 10% 分位",
            type="number",
            unit="岁",
            semantic="age",
            precision=1,
        ),
        OutputSpec(
            name="p25_age_at_death",
            question="死亡年龄 25% 分位",
            type="number",
            unit="岁",
            semantic="age",
            precision=1,
        ),
        OutputSpec(
            name="p75_age_at_death",
            question="死亡年龄 75% 分位",
            type="number",
            unit="岁",
            semantic="age",
            precision=1,
        ),
        OutputSpec(
            name="p90_age_at_death",
            question="死亡年龄 90% 分位",
            type="number",
            unit="岁",
            semantic="age",
            precision=1,
        ),
        OutputSpec(
            name="probability_to_85",
            question="活到 85 岁的概率",
            type="number",
            unit="%",
            semantic="percent",
            precision=1,
        ),
        OutputSpec(
            name="probability_to_90",
            question="活到 90 岁的概率",
            type="number",
            unit="%",
            semantic="percent",
            precision=1,
        ),
        OutputSpec(
            name="probability_to_95",
            question="活到 95 岁的概率",
            type="number",
            unit="%",
            semantic="percent",
            precision=1,
        ),
        OutputSpec(
            name="median_remaining_years",
            question="中位剩余寿命",
            type="number",
            unit="年",
            semantic="duration_years",
            precision=1,
        ),
        OutputSpec(
            name="life_expectancy_at_birth_used",
            question="使用的出生时预期寿命",
            type="number",
            unit="年",
            semantic="duration_years",
            precision=1,
            visible=False,
        ),
        OutputSpec(name="assumptions", question="模型与参数说明", type="text"),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {"current_age": 30, "sex": "男", "health": "一般"},
        },
    ),
)


def handle(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        data = LongevityInput(
            current_age=inputs["current_age"],
            sex=inputs["sex"],
            health=inputs["health"],
        )
    except ValueError as exc:
        raise CommandInputError("请检查输入。", [FieldError("inputs", str(exc))]) from exc

    result = estimate(data)
    return {
        "median_age_at_death": result.median_age_at_death,
        "p10_age_at_death": result.p10_age_at_death,
        "p25_age_at_death": result.p25_age_at_death,
        "p75_age_at_death": result.p75_age_at_death,
        "p90_age_at_death": result.p90_age_at_death,
        "probability_to_85": result.probability_to_85 * 100,
        "probability_to_90": result.probability_to_90 * 100,
        "probability_to_95": result.probability_to_95 * 100,
        "median_remaining_years": result.median_remaining_years,
        "life_expectancy_at_birth_used": result.life_expectancy_at_birth_used,
        "assumptions": (
            f"{SOURCE_NOTE} 基准出生预期寿命 {result.life_expectancy_at_birth_used:g} 年，"
            f"Gompertz b={DISPERSION_B:g}；结果条件于当前 {data.current_age} 岁。"
        ),
    }


COMMAND = Command(manifest=MANIFEST, handler=handle)
