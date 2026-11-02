"""对外接口：dict 进，dict 出。前端和其他模块只用这一层。"""

from dataclasses import fields

from yishizhuxing.constants import EDU_INFLATION, INFLATION
from yishizhuxing.costs import (
    clothing_cost,
    education_cost,
    food_cost,
    housing_cost,
    to_real,
    transport_cost,
)
from yishizhuxing.errors import LivingCostError
from yishizhuxing.profile import LivingProfile


def profile_from_dict(d: dict) -> LivingProfile:
    """从 dict 构造。字段名写错要在入口就报出来，不能静默忽略。"""
    allowed = {f.name for f in fields(LivingProfile)}
    unknown = set(d) - allowed
    if unknown:
        raise LivingCostError(
            f"未知字段 {sorted(unknown)}\n可用字段：{sorted(allowed)}")
    return LivingProfile(**d)


def calculate(d: dict) -> dict:
    """对外唯一入口：传一个 dict，返回逐年支出的 dict。

    每个数组长度都是 life_expectancy - age，下标 i 表示「第 i+1 年」。
    退休时点下标是 retire_index，收益模块从那里往后切片即可。
    nominal 是名义值（含通胀），real 是折算成今天购买力的值。
    """
    p = profile_from_dict(d)
    years = p.life_expectancy - p.age

    parts = {
        "clothing":  clothing_cost(p, years),
        "food":      food_cost(p, years),
        "housing":   housing_cost(p, years),
        "transport": transport_cost(p, years),
        "education": education_cost(p, years),
    }
    total = [sum(v) for v in zip(*parts.values())]

    return {
        "years": years,
        "retire_index": p.retire_age - p.age,
        "inflation": INFLATION,
        "edu_inflation": EDU_INFLATION,
        "nominal": {**parts, "total": total},
        "real": {k: to_real(v) for k, v in {**parts, "total": total}.items()},
    }
