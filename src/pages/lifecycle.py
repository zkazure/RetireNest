"""全周期仿真页：同一份画像驱动三条命令，输出五类视图。"""

from __future__ import annotations

from pages.models import PageExecution, PageField, PageManifest, PagePreset, PageSection

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
        PageField(name="income", command=PROJECT, allow_custom=True),
        PageField(name="assets", command=PROJECT, allow_custom=True),
        PageField(name="debt", command=PROJECT, allow_custom=True),
    ),
)

SPENDING = PageSection(
    id="spending",
    title="支出",
    fields=(
        PageField(name="expense", command=PROJECT, allow_custom=True),
        PageField(
            name="retirement_expense",
            command=PROJECT,
            required=False,
            allow_custom=True,
            hint="留空则按当前每月支出计算。",
        ),
        PageField(name="entertainment", command=PROJECT, allow_custom=True),
        PageField(name="travel", command=PROJECT, allow_custom=True),
    ),
)

PLAN = PageSection(
    id="plan",
    title="规划与策略",
    description="退休年龄留空时按法定规则推导；策略对比会在这个画像上再套五个预设。",
    fields=(
        PageField(name="retirement_age", command=PROJECT, required=False, allow_custom=True),
        PageField(name="children", command=PROJECT, allow_custom=True),
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

NAILONG = PagePreset(
    id="nailong",
    label="奶龙",
    description="34 岁 · 深圳 · 月入两万多，想 60 岁退休",
    values={
        "sex": "男",
        "city": "深圳",
        "birth_date": "1992-03-15",
        "income": "20k30k",
        "assets": "100w200w",
        "debt": "10w30w",
        "expense": "10k15k",
        "retirement_expense": "6k10k",
        "entertainment": "mid",
        "travel": "once",
        "retirement_age": "60",
        "children": "none",
    },
)


MANIFEST = PageManifest(
    id="retirement.lifecycle",
    version="2.1.0",
    title="一辈子的现金流",
    description="填几个选择题，看工作期与退休期的收支、资产轨迹，以及不同活法的差别。",
    sections=(BASIC, MONEY, SPENDING, PLAN),
    executions=(
        PageExecution(command=PROJECT, inputs=_INPUTS),
        PageExecution(command=SIMULATE, inputs=_INPUTS),
        PageExecution(command=COMPARE, inputs=_INPUTS),
    ),
    presets=(NAILONG,),
)

PAGES = {MANIFEST.id: MANIFEST}
