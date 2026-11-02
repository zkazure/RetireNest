"""基础退休规划的确定性测算。

公式与前端演示保持一致，便于和 contracts/plan-response.example.json 对拍：

    实际回报率 = (1 + 名义回报率) / (1 + 通胀率) - 1
    退休资金目标 = 退休后年净支出 × 年金现值系数 ÷ (1 + 实际回报率)^退休年数

金额统一用今天的购买力；工作期每年年末计入 12 个月结余，退休后每年年末支取
max(退休月支出 - 月养老金, 0) × 12。负债直接抵减资产，不另算利息。
"""

from __future__ import annotations

import math
from dataclasses import replace

from plan.models import PlanInput, PlanResult, ProjectionPoint, Scenario
from plan.validation import validate

SCENARIO_SPECS = (
    ("conservative", "保守情景", -1.0),
    ("baseline", "基准情景", 0.0),
    ("optimistic", "乐观情景", 1.0),
)


def calculate(plan_input: PlanInput) -> PlanResult:
    """计算基础结果。输入必须先通过 `validation.validate()`。"""
    errors = validate(plan_input)
    if errors:
        raise ValueError(errors[0].message)

    years_to_retirement = plan_input.retirement_age - plan_input.age
    retirement_years = plan_input.life_expectancy - plan_input.retirement_age
    real_return = (1 + plan_input.nominal_return / 100) / (1 + plan_input.inflation / 100) - 1

    def annuity(years: int) -> float:
        if abs(real_return) < 1e-9:
            return float(years)
        return math.expm1(years * math.log1p(real_return)) / real_return

    annual_need = max(0.0, plan_input.retirement_expense - plan_input.monthly_pension) * 12
    target = annual_need * annuity(retirement_years) / (1 + real_return) ** retirement_years
    monthly_surplus = plan_input.monthly_income - plan_input.monthly_expense
    net_assets = plan_input.assets - plan_input.debt
    projected = net_assets * (
        1 + real_return
    ) ** years_to_retirement + monthly_surplus * 12 * annuity(years_to_retirement)
    required_monthly_saving = max(
        0.0,
        (target - net_assets * (1 + real_return) ** years_to_retirement)
        / annuity(years_to_retirement)
        / 12,
    )

    points = [ProjectionPoint(age=plan_input.age, assets=net_assets)]
    balance = net_assets
    depleted_age: int | None = None
    for age in range(plan_input.age + 1, plan_input.life_expectancy + 1):
        balance = balance * (1 + real_return) + (
            monthly_surplus * 12 if age <= plan_input.retirement_age else -annual_need
        )
        if age >= plan_input.retirement_age and balance < 0 and depleted_age is None:
            depleted_age = age
        points.append(ProjectionPoint(age=age, assets=balance))

    coverage = max(0.0, projected / target * 100) if target > 0 else 100.0
    return PlanResult(
        years_to_retirement=years_to_retirement,
        retirement_years=retirement_years,
        real_return=real_return,
        monthly_surplus=monthly_surplus,
        target=target,
        projected=projected,
        gap=max(0.0, target - projected),
        coverage=coverage,
        required_monthly_saving=required_monthly_saving,
        points=tuple(points),
        depleted_age=depleted_age,
    )


def build_scenarios(plan_input: PlanInput) -> list[Scenario]:
    """只调整名义年回报，生成保守、基准、乐观三种情景。"""
    scenarios: list[Scenario] = []
    for scenario_id, label, delta in SCENARIO_SPECS:
        rate = max(-5.0, min(15.0, plan_input.nominal_return + delta))
        result = calculate(replace(plan_input, nominal_return=rate))
        scenarios.append(
            Scenario(
                id=scenario_id,
                label=label,
                nominal_return=rate,
                target=result.target,
                projected=result.projected,
                gap=result.gap,
            )
        )
    return scenarios


def build_explanation(plan_input: PlanInput, result: PlanResult) -> str:
    """生成规则解读；本期不接 LLM，控制在两句话内，避免 PDF 溢出。"""
    if result.gap > 0:
        return (
            f"按当前假设，距离退休还有 {result.years_to_retirement} 年，"
            f"每月结余 {result.monthly_surplus:,.0f} 元，"
            f"退休时预计缺口 {result.gap / 10000:.1f} 万元。"
            "可以先从收支、退休年龄和养老金假设入手调整。"
        )
    return (
        f"按当前假设，预计退休资产可以覆盖目标，目标准备度约 {result.coverage:.0f}%。"
        "建议定期更新真实收支和养老金假设，确认计划仍符合期待。"
    )
