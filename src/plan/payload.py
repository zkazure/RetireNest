"""把标准化输入与测算结果组装成对外负载。

`POST /api/retirement/plan` 与 `plan.retirement` 命令共用这些构造器，
两个入口因此不会各自维护一份字段名和结构。
"""

from __future__ import annotations

from plan.models import PlanInput, PlanResult, Scenario


def input_payload(plan_input: PlanInput) -> dict[str, object]:
    """回显参与计算的标准化输入，前端命名用 camelCase。"""
    return {
        "city": plan_input.city,
        "age": plan_input.age,
        "retirementAge": plan_input.retirement_age,
        "lifeExpectancy": plan_input.life_expectancy,
        "monthlyIncome": plan_input.monthly_income,
        "monthlyExpense": plan_input.monthly_expense,
        "assets": plan_input.assets,
        "debt": plan_input.debt,
        "retirementExpense": plan_input.retirement_expense,
        "monthlyPension": plan_input.monthly_pension,
        "nominalReturn": plan_input.nominal_return,
        "inflation": plan_input.inflation,
    }


def result_payload(result: PlanResult) -> dict[str, object]:
    """汇总指标与资产轨迹。"""
    return {
        "yearsToRetirement": result.years_to_retirement,
        "retirementYears": result.retirement_years,
        "realReturn": result.real_return,
        "monthlySurplus": result.monthly_surplus,
        "target": result.target,
        "projected": result.projected,
        "gap": result.gap,
        "coverage": result.coverage,
        "requiredMonthlySaving": result.required_monthly_saving,
        "points": [{"age": point.age, "assets": point.assets} for point in result.points],
        "depletedAge": result.depleted_age,
    }


def scenario_payload(scenario: Scenario) -> dict[str, object]:
    """单个情景的对比结果。"""
    return {
        "id": scenario.id,
        "label": scenario.label,
        "nominal_return": scenario.nominal_return,
        "target": scenario.target,
        "projected": scenario.projected,
        "gap": scenario.gap,
    }
