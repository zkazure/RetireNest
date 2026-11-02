# pages：页面清单

`pages/` 把“页面由哪些字段组成、怎么分组、提交时调用哪些命令”写成纯数据。
字段的问题文案、类型、单位、选项和约束都留在命令 manifest 里，页面只引用
`(command, input)`；前端不再持有任何业务字段配置。

解析结果由 `GET /api/pages/{page_id}` 返回，协议见
[docs/command-protocol.md](../../docs/command-protocol.md)。

## 文件

- `models.py`：`PageManifest`、`PageSection`、`PageField`、`PageToggle`、`PageExecution`、`PageRule`。
- `retirement.py`：退休规划主页的清单，8 个分组、39 个字段、5 条执行、3 个开关、4 条跨字段规则。
- `resolve.py`：校验引用并解析成前端 JSON，负责文案取值与约束交集。

## 解析规则

- `label` 只能来自来源命令的 `question`；页面模块不写问题文案。
- 同一字段被多个命令消费时，`min`/`max`/`precision`/`max_length` 取所有消费命令的交集，每次请求现算；交集为空直接报错。
- `required` 取所有消费命令的并集；带 `required_when` 的输入按必填处理，可见性由 `visible_when` 控制。
- `defaultValue` 优先取来源命令，其次取任一消费命令的默认值。
- 渲染类型取来源命令的类型；消费命令必须能接受这个类型（`integer` 可被 `number` 接受，`enum` 可被 `text` 接受，反之不行）。
- 每个字段至少被一条执行引用，每条执行的每个参数都能落到字段；出现死字段或悬空参数即报错。
- 执行清单里的命令必须已注册；分组开关必须先声明再被引用。

## 新增字段

1. 确认目标命令的 `input` 已存在（没有就先加命令输入）。
2. 在 `retirement.py` 对应 `PageSection.fields` 里加 `PageField(name=..., command=...)`。
3. 如果字段要提交给别的命令，在相应 `PageExecution.inputs` 里加映射。
4. 运行 `uv run pytest tests/test_pages.py`，它会检查引用、交集和夹具。

`tests/fixtures/retirement-page.json` 是页面响应的快照，由
`tests/test_pages.py::test_page_fixture_matches_endpoint` 对比；改页面后重新生成：

```bash
cd src
uv run python - <<'PY'
import json
from fastapi.testclient import TestClient
from api.app import app
body = TestClient(app).get("/api/pages/retirement").json()
with open("tests/fixtures/retirement-page.json", "w", encoding="utf-8") as handle:
    json.dump(body, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY
```

前端测试直接读取同一份夹具，避免前后端各造一份数据。

## 边界

- 不在这里做测算，也不决定结果页怎么画。
- 不写业务文案；分组标题和提示除外，它们只描述页面结构。
- 页面清单只登记在 `PAGES`，`GET /api/pages/{id}` 不会扫描目录。
