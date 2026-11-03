"""全周期仿真页：同一份画像驱动三条命令，输出五类视图。"""

from __future__ import annotations

from pages.models import PageExecution, PageField, PageManifest, PageSection

PROJECT = "lifecycle.project"
SIMULATE = "lifecycle.simulate"
COMPARE = "strategy.compare"

BASIC = PageSection(
    id="basic",
    title="基本情况",
    fields=(
        PageField(name="sex", command=PROJECT),
        PageField(name="city", command=PROJECT),
        PageField(name="birth_date", command=PROJECT),
        PageField(name="category", command=PROJECT, required=False),
    ),
)

MONEY = PageSection(
    id="money",
    title="收入与资产",
    fields=(
        PageField(name="income", command=PROJECT),
        PageField(name="assets", command=PROJECT),
        PageField(name="debt", command=PROJECT),
    ),
)

SPENDING = PageSection(
    id="spending",
    title="支出",
    fields=(
        PageField(name="expense", command=PROJECT),
        PageField(
            name="retirement_expense",
            command=PROJECT,
            required=False,
            hint="留空则按当前每月支出计算。",
        ),
        PageField(name="entertainment", command=PROJECT),
        PageField(name="travel", command=PROJECT),
    ),
)

PLAN = PageSection(
    id="plan",
    title="规划与策略",
    description="退休年龄留空时按法定规则推导；策略对比会在这个画像上再套五个预设。",
    fields=(
        PageField(name="retirement_age", command=PROJECT, required=False),
        PageField(name="children", command=PROJECT),
    ),
)

_INPUTS = {
    "sex": "sex",
    "city": "city",
    "birth_date": "birth_date",
    "category": "category",
    "income": "income",
    "expense": "expense",
    "assets": "assets",
    "debt": "debt",
    "retirement_expense": "retirement_expense",
    "retirement_age": "retirement_age",
    "travel": "travel",
    "entertainment": "entertainment",
    "children": "children",
}

MANIFEST = PageManifest(
    id="retirement.lifecycle",
    version="2.0.0",
    title="一辈子的现金流",
    description="填几个选择题，看工作期与退休期的收支、资产轨迹，以及不同活法的差别。",
    sections=(BASIC, MONEY, SPENDING, PLAN),
    executions=(
        PageExecution(command=PROJECT, inputs=_INPUTS),
        PageExecution(command=SIMULATE, inputs=_INPUTS),
        PageExecution(command=COMPARE, inputs=_INPUTS),
    ),
)

PAGES = {MANIFEST.id: MANIFEST}
