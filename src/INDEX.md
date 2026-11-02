# src 目录索引

一个目录对应一个用途：领域计算各占一个目录，横切的测试与脚本单列。新增目录时在下面加一行，文件级的细节写在该目录自己的 `README.md` 里。

## 领域计算

- `deposit/` — 资产型被动收入：银行活期存款收益。
- `pension/` — 权益型被动收入：城镇职工基本养老保险的月养老金测算。
- `medical/` — 医疗消费预算：输入年龄、城市和医保类型，输出当前年龄段的年度/月均参考值；调整系数暂为演示假设。
- `living/` — 衣食住行：逐年测算穿衣、饮食、住房、交通与子女教育五项支出，给出名义值和实际值。
- `plan/` — 基础退休规划聚合：消费 12 个基础字段，输出目标、预计资产、缺口、资产曲线和三情景；扩展模块由各自命令测算。

## 支撑

- `commands/` — 可发现命令协议：manifest、输入校验、注册表，以及 plan / medical / pension / deposit / living 五个适配器。协议见 `docs/command-protocol.md`。
- `pages/` — 页面清单：引用命令输入组成分组、开关与执行清单，由 `GET /api/pages/{page_id}` 提供给前端。细节见 `pages/README.md`。
- `api/` — FastAPI 接入层：`POST /api/retirement/plan`、`GET/POST /api/commands` 与 `GET /api/pages/{page_id}`；负责请求校验、字段映射、错误映射与响应组装。
- `tests/` — 全部 pytest 用例，按被测目录命名，例如 `test_rates.py` 对应 `deposit/rates.py`、`test_living.py` 对应 `living/`。在 `src/` 下执行 `uv run pytest`。
- `tools/` — 离线维护脚本，不参与运行时。目前只有 `fetch_rates.py`，抓银行活期利率供人工核对。
