"""衣食住行逐年支出命令。"""

from __future__ import annotations

from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from living import calculate
from living.constants import (
    CITY_TIER,
    CLOTHING_FREQ,
    CLOTHING_GRADE,
    COMMUTE_BASE,
    COOKING_COEF,
    EXPECTED_CHILDREN,
    LIFE_EXPECTANCY,
    LIFESTYLE_EDU,
    PARTNER_BASE,
    TRIP_ANNUAL,
    VISIT_HOME_ANNUAL,
)
from living.errors import LivingCostError

CITIES = tuple(CITY_TIER)
"""当前生活支出模块支持的 44 个城市。"""


MANIFEST = CommandManifest(
    id="living.calculate",
    version="1.0.0",
    question="退休前后每年衣食住行要花多少钱？",
    description="逐年测算穿衣、饮食、住房、交通和子女教育，给出名义值与实际值。",
    inputs=(
        InputSpec(
            name="age",
            question="你现在多少岁？",
            type="integer",
            unit="岁",
            constraints={"min": 18, "max": 120},
        ),
        InputSpec(
            name="city",
            question="你现在居住的城市？",
            type="enum",
            options=CITIES,
        ),
        InputSpec(
            name="monthly_expense",
            question="当前每月总支出（含通勤、正装、外卖）？",
            type="number",
            unit="元/月",
            constraints={"min": 0.01, "max": 1_000_000_000},
        ),
        InputSpec(
            name="child_age_now",
            question="现有孩子年龄（没有孩子可留空）？",
            type="integer",
            unit="岁",
            required=False,
            constraints={"min": 0, "max": 50},
        ),
        InputSpec(
            name="retire_age",
            question="期望退休年龄？",
            type="integer",
            unit="岁",
            required=False,
            default=60,
            constraints={"min": 18, "max": 120},
        ),
        InputSpec(
            name="life_expectancy",
            question="规划至年龄？",
            type="integer",
            unit="岁",
            required=False,
            default=LIFE_EXPECTANCY,
            constraints={"min": 18, "max": 120},
        ),
        InputSpec(
            name="partner",
            question="退休生活安排？",
            type="enum",
            options=tuple(PARTNER_BASE),
            required=False,
            default="还没想好",
        ),
        InputSpec(
            name="children",
            question="子女计划？",
            type="enum",
            options=tuple(EXPECTED_CHILDREN),
            required=False,
            default="还没想好",
        ),
        InputSpec(
            name="housing_plan",
            question="住房打算？",
            type="enum",
            options=("一直租房", "买房自住", "已有房", "还没想"),
            required=False,
            default="还没想",
        ),
        InputSpec(
            name="lifestyle",
            question="退休后的生活水平？",
            type="enum",
            options=tuple(LIFESTYLE_EDU),
            required=False,
            default="舒适",
        ),
        InputSpec(
            name="retire_city",
            question="退休居住城市（留空表示与现在同城）？",
            type="enum",
            options=CITIES,
            required=False,
        ),
        InputSpec(
            name="clothing_freq",
            question="退休后购衣频率？",
            type="enum",
            options=tuple(CLOTHING_FREQ),
            required=False,
            default="一般",
        ),
        InputSpec(
            name="clothing_grade",
            question="衣物档次？",
            type="enum",
            options=tuple(CLOTHING_GRADE),
            required=False,
            default="品牌",
        ),
        InputSpec(
            name="cooking",
            question="饮食方式？",
            type="enum",
            options=tuple(COOKING_COEF),
            required=False,
            default="一半一半",
        ),
        InputSpec(
            name="extra_food",
            question="有三餐外饮食需求？",
            type="boolean",
            required=False,
            default=False,
        ),
        InputSpec(
            name="retire_commute",
            question="退休后主要出行方式？",
            type="enum",
            options=tuple(COMMUTE_BASE),
            required=False,
            default="公交地铁",
        ),
        InputSpec(
            name="trip_level",
            question="旅游频率？",
            type="enum",
            options=tuple(TRIP_ANNUAL),
            required=False,
            default="偶尔国内",
        ),
        InputSpec(
            name="visits_home",
            question="探亲频率？",
            type="enum",
            options=tuple(VISIT_HOME_ANNUAL),
            required=False,
            default="一年一两次",
        ),
    ),
    outputs=(
        OutputSpec(name="years", question="测算年数", type="integer", unit="年"),
        OutputSpec(
            name="retire_index",
            question="退休在数组中的下标",
            type="integer",
            visible=False,
        ),
        OutputSpec(name="inflation", question="生活支出通胀假设", type="number", semantic="ratio"),
        OutputSpec(
            name="edu_inflation",
            question="教育支出通胀假设",
            type="number",
            semantic="ratio",
        ),
        OutputSpec(
            name="nominal",
            question="逐年名义支出",
            type="object",
            unit="元/年",
            semantic="money_per_year_nominal",
            time_axis={"start": "age", "step_years": 1, "length_field": "years"},
        ),
        OutputSpec(
            name="real",
            question="逐年实际支出（今天购买力）",
            type="object",
            unit="元/年",
            semantic="money_per_year_real",
            time_axis={"start": "age", "step_years": 1, "length_field": "years"},
        ),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {"age": 30, "city": "珠海", "monthly_expense": 9000},
        },
    ),
)
"""衣食住行命令的 manifest。"""


def handle(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        return calculate({key: value for key, value in inputs.items() if value is not None})
    except LivingCostError as exc:
        raise CommandInputError(str(exc)) from exc


COMMAND = Command(manifest=MANIFEST, handler=handle)
"""注册表使用的命令对象。"""
