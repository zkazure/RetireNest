"""退休规划主页的页面清单。

字段顺序即页面顺序；每个字段的文案、类型、单位、选项与约束都来自它声明的
命令 manifest。执行清单决定提交时调用哪些命令、字段如何映射。
"""

from __future__ import annotations

from pages.models import (
    PageExecution,
    PageField,
    PageManifest,
    PageRule,
    PageSection,
    PageToggle,
)

PLAN = "plan.retirement"
LIVING = "living.calculate"
MEDICAL = "medical.estimate"
PENSION = "pension.basic"
DEPOSIT = "deposit.demand"

BASIC = PageSection(
    id="basic",
    title="基本情况",
    fields=(
        PageField(name="city", command=LIVING),
        PageField(name="age", command=PLAN),
        PageField(name="retire_age", command=PLAN),
        PageField(name="life_expectancy", command=PLAN),
    ),
)

FINANCE = PageSection(
    id="finance",
    title="收支与资产",
    fields=(
        PageField(name="monthly_income", command=PLAN),
        PageField(name="monthly_expense", command=PLAN),
        PageField(name="assets", command=PLAN),
        PageField(name="debt", command=PLAN),
    ),
)

RETIREMENT = PageSection(
    id="retirement",
    title="期待的退休生活",
    description="以下金额按今天的购买力填写；预估养老金为自行估计值。",
    fields=(
        PageField(name="retirement_expense", command=PLAN),
        PageField(name="monthly_pension", command=PLAN),
    ),
)

LIVING_SECTION = PageSection(
    id="living",
    title="生活与家庭偏好",
    description="这些偏好会交给生活支出命令，测算退休前后的衣食住行花费。",
    fields=(
        PageField(name="partner", command=LIVING),
        PageField(name="children", command=LIVING),
        PageField(name="child_age_now", command=LIVING, hint="没有孩子可留空。"),
        PageField(name="housing_plan", command=LIVING),
        PageField(name="lifestyle", command=LIVING),
        PageField(name="retire_city", command=LIVING, hint="留空表示与现在同城。"),
        PageField(name="clothing_freq", command=LIVING),
        PageField(name="clothing_grade", command=LIVING),
        PageField(name="cooking", command=LIVING),
        PageField(name="extra_food", command=LIVING),
        PageField(name="retire_commute", command=LIVING),
        PageField(name="trip_level", command=LIVING),
        PageField(name="visits_home", command=LIVING),
    ),
)

MEDICAL_SECTION = PageSection(
    id="medical",
    title="医疗预算信息",
    description="启用后补充医保情况，单独测算医疗预算。",
    toggle=PageToggle(name="medical_enabled", label="填写医保信息"),
    fields=(PageField(name="insurance", command=MEDICAL),),
)

PENSION_SECTION = PageSection(
    id="pension",
    title="养老金详细信息",
    description="启用后按缴费年限、指数与账户余额测算养老金。",
    toggle=PageToggle(name="pension_enabled", label="填写养老金信息"),
    fields=(
        PageField(name="birth_date", command=PENSION),
        PageField(name="gender", command=PENSION),
        PageField(
            name="category",
            command=PENSION,
            visible_when=({"field": "gender", "equals": "女"},),
        ),
        PageField(name="contribution_years", command=PENSION),
        PageField(name="average_index", command=PENSION),
        PageField(name="account_balance", command=PENSION),
        PageField(name="calculation_base", command=PENSION),
        PageField(name="prior_monthly_wage", command=PENSION),
        PageField(name="annual_adjustment", command=PENSION, hint="留空由后端取默认值。"),
    ),
)

DEPOSIT_SECTION = PageSection(
    id="deposit",
    title="存款收益信息",
    description="启用后测算这笔活期存款的到期利息；本金与利率按十进制字符串提交。",
    toggle=PageToggle(name="deposit_enabled", label="填写存款信息"),
    fields=(
        PageField(name="principal", command=DEPOSIT),
        PageField(name="annual_rate", command=DEPOSIT, hint="留空由后端取默认值。"),
        PageField(name="start_date", command=DEPOSIT),
        PageField(name="end_date", command=DEPOSIT),
    ),
)

ASSUMPTIONS = PageSection(
    id="assumptions",
    title="测算假设",
    description="以下回报与通胀以百分数填写。",
    fields=(
        PageField(name="nominal_return", command=PLAN),
        PageField(name="inflation", command=PLAN),
    ),
)

MANIFEST = PageManifest(
    id="retirement",
    version="1.0.0",
    title="我的规划信息",
    description="基础信息用于退休资金测算；生活偏好与可选模块会分别调用对应命令，结果一并展示。",
    sections=(
        BASIC,
        FINANCE,
        RETIREMENT,
        LIVING_SECTION,
        MEDICAL_SECTION,
        PENSION_SECTION,
        DEPOSIT_SECTION,
        ASSUMPTIONS,
    ),
    executions=(
        PageExecution(
            command=PLAN,
            inputs={
                "city": "city",
                "age": "age",
                "retire_age": "retire_age",
                "life_expectancy": "life_expectancy",
                "monthly_income": "monthly_income",
                "monthly_expense": "monthly_expense",
                "assets": "assets",
                "debt": "debt",
                "retirement_expense": "retirement_expense",
                "monthly_pension": "monthly_pension",
                "nominal_return": "nominal_return",
                "inflation": "inflation",
            },
        ),
        PageExecution(
            command=LIVING,
            inputs={
                "age": "age",
                "city": "city",
                "monthly_expense": "monthly_expense",
                "child_age_now": "child_age_now",
                "retire_age": "retire_age",
                "life_expectancy": "life_expectancy",
                "partner": "partner",
                "children": "children",
                "housing_plan": "housing_plan",
                "lifestyle": "lifestyle",
                "retire_city": "retire_city",
                "clothing_freq": "clothing_freq",
                "clothing_grade": "clothing_grade",
                "cooking": "cooking",
                "extra_food": "extra_food",
                "retire_commute": "retire_commute",
                "trip_level": "trip_level",
                "visits_home": "visits_home",
            },
        ),
        PageExecution(
            command=MEDICAL,
            inputs={"age": "age", "city": "city", "insurance": "insurance"},
            toggle="medical_enabled",
        ),
        PageExecution(
            command=PENSION,
            inputs={
                "birth_date": "birth_date",
                "gender": "gender",
                "category": "category",
                "contribution_years": "contribution_years",
                "average_index": "average_index",
                "account_balance": "account_balance",
                "calculation_base": "calculation_base",
                "prior_monthly_wage": "prior_monthly_wage",
                "annual_adjustment": "annual_adjustment",
            },
            toggle="pension_enabled",
        ),
        PageExecution(
            command=DEPOSIT,
            inputs={
                "principal": "principal",
                "annual_rate": "annual_rate",
                "start_date": "start_date",
                "end_date": "end_date",
            },
            toggle="deposit_enabled",
        ),
    ),
    rules=(
        PageRule(
            type="lessThan",
            left="age",
            right="retire_age",
            message="期望退休年龄需要大于当前年龄。",
        ),
        PageRule(
            type="lessThan",
            left="retire_age",
            right="life_expectancy",
            message="规划至年龄需要大于期望退休年龄。",
        ),
        PageRule(
            type="minimumDifference",
            left="age",
            right="child_age_now",
            minimum=15,
            message="当前年龄与孩子年龄至少相差 15 岁。",
        ),
        PageRule(
            type="dateBefore",
            left="start_date",
            right="end_date",
            message="存款结束日期需要晚于开始日期。",
        ),
    ),
)
"""退休规划主页的页面清单。"""

PAGES: dict[str, PageManifest] = {MANIFEST.id: MANIFEST}
"""当前可用的页面；新增页面时在这里登记。"""
