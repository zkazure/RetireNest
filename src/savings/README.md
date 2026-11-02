# savings：储蓄增长与目标倒推

复利与年金原语，供 `plan/` 和 `savings.*` 命令共用。

## 口径

- 金额单位为元；收益率与通胀率用百分数（5 表示 5%）；年限为整数。
- 实际年回报率 = `(1 + 名义年回报率) / (1 + 通胀率) - 1`。
- 默认按年复利、期末投入，与 `plan.engine` 一致；`compounding="monthly"` 与 `timing="begin"` 可选。
- 金额按今天的购买力计算；月投入按实际值恒定，名义上随通胀增长。

## 文件

- `models.py`：输入输出 dataclass，含范围校验。
- `rates.py`：`real_rate`、`period_rate`、`annuity_factor`、`future_value`。
- `projection.py`：`project()`，给定储蓄与月投入预测未来余额。
- `goal.py`：`required_contribution()`，给定目标反推月投入。

## 与 plan 的关系

`plan.engine` 调用 `savings.rates.real_rate` 与 `annuity_factor`，不再自己维护一套年金公式。
`tests/test_plan_engine.py` 有两组交叉校验：同口径下 `project()` 必须等于 `plan.projected`，
`required_contribution()` 必须等于 `plan.required_monthly_saving`，误差上限 `rel=1e-12`。

## 不做

- 不做税费、手续费、收益波动；这些分别由 `simulation/` 和后续税务工具处理。
- 不做分段收益率或现金流时点表；每年只用一个固定实际收益率。
