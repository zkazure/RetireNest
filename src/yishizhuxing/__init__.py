"""衣食住行 · 退休后五项逐年支出计算。

对外用法：

    from yishizhuxing import calculate
    result = calculate({"age": 30, "city": "珠海", "monthly_expense": 9000})

命令行：

    python -m yishizhuxing
    python -m yishizhuxing --json '{"age":30,"city":"珠海","monthly_expense":9000}'
"""

from yishizhuxing.api import calculate, profile_from_dict
from yishizhuxing.constants import *
from yishizhuxing.costs import (
    adults_at,
    annual_mortgage,
    child_age_at,
    child_birth_user_age,
    city_tier,
    clothing_cost,
    education_cost,
    food_cost,
    house_buy_year,
    house_type,
    housing_cost,
    inflation_factor,
    ret_tier,
    stage_rate,
    to_real,
    total_living_cost,
    transport_cost,
)
from yishizhuxing.errors import LivingCostError
from yishizhuxing.profile import LivingProfile

__version__ = "1.0.0"

__all__ = [
    "LivingCostError",
    "LivingProfile",
    "adults_at",
    "annual_mortgage",
    "calculate",
    "child_age_at",
    "child_birth_user_age",
    "city_tier",
    "clothing_cost",
    "education_cost",
    "food_cost",
    "house_buy_year",
    "house_type",
    "housing_cost",
    "inflation_factor",
    "profile_from_dict",
    "ret_tier",
    "stage_rate",
    "to_real",
    "total_living_cost",
    "transport_cost",
]
