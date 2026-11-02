# Profit

目前只计算一项被动收入：银行活期存款收益。养老金等其他收入暂不在本模块范围内。

计算口径、舍入规则与已知取舍写在 `demand_deposit.py` 的模块注释里。

## 使用方法

```python
from datetime import date

from profit import DemandDeposit, calculate

deposit = DemandDeposit(
    principal="100000",
    annual_rate="0.0005",  # 可省略，默认 0.05%
    start_date=date(2026, 1, 1),
    end_date=date(2027, 1, 1),
)
result = calculate(deposit)

result.days  # 365
result.interest  # Decimal('50.69')
result.total  # Decimal('100050.69')
result.daily_rate  # Decimal('0.0000013889')，仅供展示
```

## 参数

- principal：本金，Decimal、int 或字符串，须大于 0 且最多两位小数；float 会被拒绝。
- annual_rate：年利率，类型同上，不能为负；省略时取 `rates.py` 里利率快照的等权平均（当前 0.05%），不写死在计算里。
- start_date / end_date：起止日期，结束日期必须晚于起始日期。

## 返回

- days：计息天数。
- interest：利息，单位元，保留到分。
- total：期末本息，等于本金加利息。
- daily_rate：日利率，仅供展示，不参与计算。

## 出错

参数不合法时抛 `ProfitError`（`ValueError` 的子类），消息写明是哪个参数、期望什么。

## 测试

在 `src/` 下执行：

```
uv run pytest
```
