# plan：基础退休规划测算

本期消费 12 个基础字段，计算退休资金目标、预计资产、缺口、准备度、资产曲线和三情景。医疗、养老、存款和生活偏好由各自的命令测算，不并入这里的目标与缺口。

## 口径

- 金额单位为元；`nominal_return` 与 `inflation` 用百分数（3 表示 3%）。
- 实际回报率 = (1 + 名义回报率) / (1 + 通胀率) - 1。
- 金额统一用今天的购买力；工作期每年年末计入 12 个月结余，退休后每年年末支取 max(退休月支出 - 月养老金, 0) × 12。
- 负债直接抵减资产，不另算利息；不计税费、收益波动和政策变化。
- `points` 从当前年龄到规划终点逐年连续，负资产保留在曲线上用于暴露缺口。
- `coverage` 是百分数，`gap` 不小于 0；`target` 为 0 时 `coverage` 记 100。

## 用法

```python
from plan import PlanInput, calculate, build_scenarios

plan_input = PlanInput(
    city="广州",
    age=28,
    retirement_age=55,
    life_expectancy=90,
    monthly_income=15000,
    monthly_expense=10000,
    assets=180000,
    debt=30000,
    retirement_expense=10000,
    monthly_pension=2500,
    nominal_return=3,
    inflation=2,
)
result = calculate(plan_input)
scenarios = build_scenarios(plan_input)
```

`calculate()` 会先调用 `validation.validate()`；输入不合法时抛 `ValueError`。HTTP 层在调用前用 `api.service.parse_values()` 收集字段级错误，不会走到这里。

## 验证

```bash
cd src
uv run pytest tests/test_plan_engine.py
```

默认输入与 `frontend/contracts/plan-response.example.json` 对拍；测试覆盖 points 连续性、depleted_age、三情景、利率截断、范围校验和零目标。

## 不做

- 医疗、养老、存款、生活支出的综合聚合；本期只做基础字段。
- Decimal 金额引擎；当前为了与前端示例对拍使用 float。
- LLM 解读；`build_explanation()` 只生成规则文本。
