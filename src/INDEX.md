# src 目录索引

一个目录对应一个用途：领域计算各占一个目录，横切的测试与脚本单列。新增目录时在下面加一行，文件级的细节写在该目录自己的 `README.md` 里。

## 领域计算

- `profit/` — 收入侧：目前只算银行活期存款收益，养老金待定范围。

## 支撑

- `tests/` — 全部 pytest 用例，按被测目录命名，例如 `test_demand_deposit.py` 对应 `profit/demand_deposit.py`。在 `src/` 下执行 `uv run pytest`。
- `tools/` — 离线维护脚本，不参与运行时。目前只有 `fetch_rates.py`，抓银行活期利率供人工核对。
