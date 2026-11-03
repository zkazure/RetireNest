# pages：页面清单

`pages/` 把“页面由哪些字段组成、怎么分组、提交时调用哪些命令”写成纯数据。
字段的问题文案、类型、单位、选项和约束都留在命令 manifest 里，页面只引用
`(command, input)`；前端不再持有任何业务字段配置。

解析结果由 `GET /api/pages/{page_id}` 返回，协议见
[docs/command-protocol.md](../../docs/command-protocol.md)。

## 文件

- `models.py`：`PageManifest`、`PageSection`、`PageField`、`PageToggle`、`PageExecution`、`PageRule`、`PagePreset`。
- `lifecycle.py`：全周期页清单，4 个分组、13 个字段、3 条执行、1 份示例画像，无开关与跨字段规则。
- `resolve.py`：校验引用并解析成前端 JSON，负责文案取值与约束交集。

## 解析规则

- `label` 只能来自来源命令的 `question`；页面模块不写问题文案。
- 同一字段被多个命令消费时，`min`/`max`/`precision`/`max_length` 取所有消费命令的交集，`integer` 只要有一个命令要求就是真；每次请求现算，交集为空直接报错。
- `required` 由页面字段自己声明，默认 `True`；写 `required=False` 才允许留空。标了 `False` 的字段，其所有消费命令的对应输入也必须可选，否则解析直接报错，避免“表单放行、后端 422”。命令的 `required_when` 不参与页面的必填判断；条件必填用 `visible_when`，只在满足条件时可见，可见即必答。
- `defaultValue` 优先取来源命令，其次取任一消费命令的默认值。
- 档位字段写 `allow_custom=True` 时，页面在档位之外提供「其他（自己填）」：`min`/`max`/`integer` 是从消费命令透传的自定义数值约束；任一消费命令的 `InputSpec.allow_custom` 为假则解析报错。下拉字段仍只能选，不开自定义。
- 渲染类型取来源命令的类型；消费命令必须能接受这个类型（`integer` 可被 `number` 接受，`enum` 可被 `text` 接受，反之不行）。
- 每个字段至少被一条执行引用，每条执行的每个参数都能落到字段；出现死字段或悬空参数即报错。
- 执行清单里的命令必须已注册；分组开关必须先声明再被引用。
- 示例画像的取值逐个校验：键必须是页面字段；下拉取选项值；档位取档位 key，或 `allowCustom` 为真时取范围内的数值字符串（`integer` 的档位要求整数）；日期取 `YYYY-MM-DD`；开关取布尔。允许只填一部分字段，任一取值不合法即报错。跨字段规则不参与画像校验。

## 新增示例画像

1. 在 `lifecycle.py` 里写一个 `PagePreset(id=..., label=..., description=..., values={...})`。
2. `values` 的键用页面字段名，取值按上面的校验口径；想留空的字段直接不写。
3. 把画像加进 `MANIFEST.presets`，并升一下页面 `version`。
4. 重新生成夹具，`uv run pytest tests/test_pages.py` 会检查画像取值是否对得上字段。

## 新增字段

1. 确认目标命令的 `input` 已存在（没有就先加命令输入）。
2. 在 `lifecycle.py` 对应 `PageSection.fields` 里加 `PageField(name=..., command=...)`。
3. 如果这个问题可以留空，加 `required=False`，并确认消费命令的对应输入也是 `required=False`。
4. 如果是档位字段且允许用户自己填数，加 `allow_custom=True`，并给消费命令的 `InputSpec` 设 `allow_custom=True` 与 `constraints`（`min`/`max`，需要整数再加 `integer`）。
5. 如果字段要提交给别的命令，在相应 `PageExecution.inputs` 里加映射。
6. 运行 `uv run pytest tests/test_pages.py`，它会检查引用、交集和夹具。

`tests/fixtures/lifecycle-page.json` 是页面响应的快照，由
`tests/test_pages.py::test_page_fixture_matches_endpoint` 对比；改页面后重新生成：

```bash
cd src
uv run python - <<'PY'
import json
from fastapi.testclient import TestClient
from api.app import app
body = TestClient(app).get("/api/pages/retirement.lifecycle").json()
with open("tests/fixtures/lifecycle-page.json", "w", encoding="utf-8") as handle:
    json.dump(body, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY
```

前端测试直接读取同一份夹具，避免前后端各造一份数据。

## 边界

- 不在这里做测算，也不决定结果页怎么画。
- 不写业务文案；分组标题和提示除外，它们只描述页面结构。
- 页面清单只登记在 `PAGES`，`GET /api/pages/{id}` 不会扫描目录。
