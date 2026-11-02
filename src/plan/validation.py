"""基础字段的范围与跨字段校验。

类型与必填由 API 层的映射负责；本模块只处理已经转换好的数值。
错误消息沿用前端现有中文，避免同一个字段在两端出现两套说法。
"""

from __future__ import annotations

from plan.models import FieldError, PlanInput

MAX_AMOUNT = 1_000_000_000.0
MIN_MONTHLY_EXPENSE = 0.01


def validate(plan_input: PlanInput) -> list[FieldError]:
    """返回全部可定位错误；空列表表示可以计算。"""
    errors: list[FieldError] = []

    if not 18 <= plan_input.age <= 80:
        errors.append(FieldError("age", "当前年龄需要在 18 至 80 岁之间。"))
    if plan_input.retirement_age <= plan_input.age or plan_input.retirement_age > 85:
        errors.append(FieldError("retire_age", "期望退休年龄需要大于当前年龄，且不超过 85 岁。"))
    if plan_input.life_expectancy <= plan_input.retirement_age or plan_input.life_expectancy > 110:
        errors.append(
            FieldError("life_expectancy", "规划至年龄需要大于退休年龄，且不超过 110 岁。")
        )

    amounts = (
        ("monthly_income", plan_input.monthly_income),
        ("assets", plan_input.assets),
        ("debt", plan_input.debt),
        ("retirement_expense", plan_input.retirement_expense),
        ("monthly_pension", plan_input.monthly_pension),
    )
    for field, value in amounts:
        if not 0 <= value <= MAX_AMOUNT:
            errors.append(FieldError(field, "金额需在 0 至 10 亿元之间。"))

    if not MIN_MONTHLY_EXPENSE <= plan_input.monthly_expense <= MAX_AMOUNT:
        errors.append(FieldError("monthly_expense", "当前月支出需在 0.01 至 10 亿元之间。"))

    if not 0 <= plan_input.inflation <= 10:
        errors.append(FieldError("inflation", "请将通胀设为 0%～10%。"))
    if not -5 <= plan_input.nominal_return <= 15:
        errors.append(FieldError("nominal_return", "请将名义年回报设为 -5%～15%。"))

    if not plan_input.city:
        errors.append(FieldError("city", "请填写城市。"))
    elif len(plan_input.city) > 30:
        errors.append(FieldError("city", "城市名称最多 30 个字符。"))

    return errors
