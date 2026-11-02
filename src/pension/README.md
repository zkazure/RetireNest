# Pension

城镇职工基本养老保险的月养老金测算，只算“退休时点”的静态值：

    月养老金 = 基础养老金 + 个人账户养老金

公式、口径与取舍写在 `basic_pension.py` 的模块注释里，本文件只讲用法。

## 使用方法

```python
from datetime import date
from decimal import Decimal

from pension import BasicPensionInput, calculate

inp = BasicPensionInput(
    birth_date=date(1965, 6, 1),
    gender="男",
    contribution_years=Decimal(30),
    average_index=Decimal(1),
    account_balance=Decimal(150000),
    calculation_base=Decimal(8000),  # 退休上年度本省计发基数，需要自己查
)
result = calculate(inp)

result.retirement_age_months  # 722，60 岁 2 个月（延迟退休后）
result.payout_months  # 139
result.basic_pension  # Decimal('2400.00')
result.account_pension  # Decimal('1079.14')
result.total  # Decimal('3479.14')
result.monthly_at(24)  # 退休两年后的名义月养老金
```

## 参数

- birth_date / gender / category：出生年月、性别、岗位类别；女性必须给类别（管理技术或工人），男性可省略。
- contribution_years：缴费年限，可用小数，按年计。
- average_index：平均缴费指数，0.6~3.0。
- account_balance：退休时点的个人账户储存额；本模块不做逐年累积。
- calculation_base：计发基数，元/月，由各省每年公布，必须自己传入。
- prior_monthly_wage：退休前月工资，给了才算替代率。
- annual_adjustment：年调整率，省略时取调整率快照的最近一次（当前 2.0%）。

返回 `BasicPensionResult`，字段都是可追溯的中间量或终值；`monthly_at(n)` 给退休后第
n 个月的名义月养老金。

## 参数快照

计发基数与调整率都是带来源和日期的快照，见 `params.py`。更新流程：

1. 拿到新公告后构造 `CalculationBaseQuote`（省份、月计发基数、生效年份、来源、抓取日期）。
2. 用 `upsert_base(quote)` 生成新元组，打印后贴回 `CALC_BASE_SNAPSHOT`。
3. 调整率改 `ADJUSTMENT_SNAPSHOT`；`stale()` 能列出超过一年未复核的记录。

计发基数快照初始为空：没有经过核对的数字不写进去，`base_for()` 查不到会直接报错。

## 和缺口的关系

养老金是退休后的确定性收入，缺口 = 退休后月支出 − 月养老金 − 其他被动收入。
例如月支出 6000、月养老金 3479.14，剩下 2520.86 要由资产覆盖；这部分才是 profit
与其他资产收益要回答的问题。养老金不进 profit，避免把两类收入混成一个收益率。

## 测试

在 `src/` 下执行：

```
uv run pytest
```
