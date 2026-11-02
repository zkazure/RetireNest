# portfolio：三档资产到组合收益与波动

## 档位

| 档位 | 持有 | 年化收益 | 年化波动 |
| --- | --- | --- | --- |
| high | 股票、股票型基金 | 7.4% | 20% |
| mid | 债券基金、混合基金 | 4.0% | 6% |
| low | 活期、定期存款 | 1.5% | 0.5% |

收益是名义值，波动是实际收益率的年化标准差。权益的收益由沪深 300 长期价格
指数年化 4.91% 加股息 2.5% 得到；债券由上证国债 3.57% 上浮到 4.0%。取值理由
与数据来源见 `docs/data-sources.md` §2。

## 组合

`combine(weights)` 返回 `PortfolioAssumption`：

- 期望收益 = Σ w·r，线性加权
- 波动 = √(ΣΣ w_i·w_j·σ_i·σ_j·ρ_ij)，相关系数见 `ASSUMPTIONS.CORRELATION`

股债相关取 0.1，是 `[假设]`。组合波动对相关系数不敏感：0.1 与 0 的差别不到
一个百分点。

## 与其它模块的关系

- 输入来自 `profile.Profile.allocations`（默认 30/50/20）
- 输出直接给 `simulation.generate_real_paths` 的 `annual_return_pct` 与
  `volatility_pct`
- 单一档位占 100% 时，结果与 `simulation` 直接用该档参数完全一致，测试覆盖
