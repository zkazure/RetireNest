"""由选项与少量事实推导计算参数。

推导集中在这里，是为了让下游只吃 `Profile`：页面层负责收集选项，命令层负责
校验类型，口径只在推导层写一次。
"""

from __future__ import annotations

from datetime import date
from profile.errors import ProfileError

from living.constants import CITY_COEF, CITY_TIER
from longevity import LongevityInput, estimate
from pension.retirement import retirement_age_months

PENSION_START_AGE = 22
"""开始缴费的默认年龄，毕业后进入职场。"""

MAX_CONTRIBUTION_YEARS = 35
"""缴费年限上限：现行计发公式对 35 年以上不再有额外加成。"""

MIN_INDEX = 0.6
MAX_INDEX = 3.0
"""缴费指数的上下限，对应社平工资的 60% 与 300%。"""

DEFAULT_ACCOUNT_RATE = 0.015
"""个人账户记账利率，取 2025 年公布的 1.5%，见 docs/data-sources.md §3。"""

BASE_MONTHLY_WAGE = 8_400
"""全国全口径城镇单位就业人员月平均工资，[待核]，见 docs/data-sources.md §3。"""

ACCOUNT_CONTRIBUTION_RATE = 0.08
"""个人账户按缴费工资的 8% 记账。"""


def city_base_wage(city: str) -> float:
    """城市计发基数：全国月均工资乘城市系数，未知城市按二线处理。"""
    tier = CITY_TIER.get(city, "二线")
    return BASE_MONTHLY_WAGE * CITY_COEF[tier]


def contribution_years(retirement_age: int, start_age: int = PENSION_START_AGE) -> int:
    if not 0 < start_age < retirement_age:
        raise ProfileError(f"退休年龄 {retirement_age} 必须大于起缴年龄 {start_age}。")
    return min(retirement_age - start_age, MAX_CONTRIBUTION_YEARS)


def contribution_index(monthly_income: float, base_wage: float) -> float:
    if base_wage <= 0:
        raise ProfileError("计发基数必须为正。")
    ratio = monthly_income / base_wage
    return round(min(max(ratio, MIN_INDEX), MAX_INDEX), 4)


def account_balance(
    monthly_income: float,
    years: int,
    rate: float = DEFAULT_ACCOUNT_RATE,
) -> float:
    """个人账户余额：每年缴入工资的 8%，按记账利率计复利。"""
    if years <= 0:
        return 0.0
    yearly = monthly_income * 12 * ACCOUNT_CONTRIBUTION_RATE
    if rate <= 0:
        return yearly * years
    return yearly * (((1 + rate) ** years - 1) / rate)


def statutory_retirement_age(
    birth_date: date,
    gender: str,
    category: str | None = None,
) -> int:
    """按渐进式延迟退休规则算，取整到周岁（不足一年按整年计）。"""
    return retirement_age_months(birth_date, gender, category) // 12


def realistic_plan_until(age: int, sex: str, health: str = "一般") -> int:
    """规划终点取寿命的 75% 分位：宁可多备，不可少备。"""
    result = estimate(LongevityInput(current_age=age, sex=sex, health=health))
    return round(result.p75_age_at_death)
