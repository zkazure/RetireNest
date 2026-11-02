"""把页面提交的选项解析成 `Profile`。"""

from __future__ import annotations

from datetime import date
from profile import tiers
from profile.derive import (
    account_balance,
    city_base_wage,
    contribution_index,
    contribution_years,
    realistic_plan_until,
    statutory_retirement_age,
)
from profile.errors import ProfileError
from profile.schema import DEFAULT_ALLOCATION, PensionParams, Profile
from typing import Any


def build_profile(
    *,
    age: int,
    sex: str,
    city: str,
    income_tier: str,
    expense_tier: str,
    asset_tier: str,
    debt_tier: str,
    retirement_expense_tier: str,
    travel_tier: str,
    entertainment_tier: str,
    children_tier: str,
    retirement_age: int | None = None,
    plan_until: int | None = None,
    birth_date: date | None = None,
    category: str | None = None,
    allocations: dict[str, float] | None = None,
) -> Profile:
    """选项进、画像出。未给退休年龄时按法定规则推导。"""
    income = tiers.INCOME.get(income_tier).amount
    base_wage = city_base_wage(city)
    if retirement_age is None:
        if birth_date is None:
            raise ProfileError("推导退休年龄需要出生日期。")
        retirement_age = statutory_retirement_age(birth_date, sex, category)
    if plan_until is None:
        plan_until = realistic_plan_until(age, sex)
    years = contribution_years(retirement_age)
    return Profile(
        age=age,
        sex=sex,
        city=city,
        retirement_age=retirement_age,
        plan_until=plan_until,
        monthly_income=income,
        monthly_expense=tiers.EXPENSE.get(expense_tier).amount,
        assets=tiers.ASSETS.get(asset_tier).amount,
        debt=tiers.DEBT.get(debt_tier).amount,
        retirement_expense=tiers.RETIRE_EXPENSE.get(retirement_expense_tier).amount,
        travel_trips=tiers.TRAVEL.get(travel_tier).amount,
        entertainment_monthly=tiers.ENTERTAINMENT.get(entertainment_tier).amount,
        children=int(tiers.CHILDREN.get(children_tier).amount),
        pension=PensionParams(
            years=years,
            index=contribution_index(income, base_wage),
            account_balance=account_balance(income, years),
            base_wage=base_wage,
        ),
        allocations=dict(allocations or DEFAULT_ALLOCATION),
    )


def tier_amount(table: tiers.TierTable, value: Any) -> float:
    """给命令层用：把选项值换成数值，缺省或非法都报错。"""
    if not isinstance(value, str):
        raise ProfileError(f"{table.name} 需要选项值（字符串）。")
    return table.get(value).amount
