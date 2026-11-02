# api：退休规划 HTTP 接入层

FastAPI 暴露三组端点：

- `GET /api/pages/{page_id}`：返回页面清单，主页据此渲染表单并决定提交时执行哪些命令。
- `GET /api/commands`：返回协议版本和五个领域命令的 manifest。
- `POST /api/commands/{command_id}`：执行单个命令，请求 `{version, inputs}`，返回 `{command_id, version, outputs, meta}`。
- `POST /api/retirement/plan`：过渡接口，把旧请求的 `values` 映射成 12 个基础字段，返回与 `frontend/contracts/plan-response.example.json` 同构的响应；新前端不再调用。

协议、页面清单、错误码和 manifest 字段见 [docs/command-protocol.md](../../docs/command-protocol.md)。页面清单只描述结构，执行业务仍走命令端点。

## 启动

日常推荐在仓库根目录用一键启动器：

```bash
uv run --project src python run.py          # 开发模式，5173
uv run --project src python run.py --prod   # 单端口演示，8000
```

手动启动：

```bash
cd src
uv sync
uv run uvicorn api.app:app --host 127.0.0.1 --port 8000
```

前端开发服务器通过 `/api` 代理访问这里，见 `frontend/vite.config.ts`；本层不开启 CORS。生产模式由 `run.py --prod` 先构建前端；`api/app.py` 在 `frontend/dist` 存在时会把它挂载到 `/`，API 和 `/docs` 仍优先匹配。

## 请求

```json
{
  "template_id": "retirenest-retirement",
  "schema_version": "1.0.0",
  "values": {
    "city": "广州", "age": 28, "retire_age": 55, "life_expectancy": 90,
    "monthly_income": 15000, "monthly_expense": 10000,
    "assets": 180000, "debt": 30000,
    "retirement_expense": 10000, "monthly_pension": 2500,
    "nominal_return": 3, "inflation": 2
  }
}
```

- 只读取 12 个基础字段；医疗、养老、存款、生活偏好等扩展字段静默忽略，保证旧请求仍可用。
- `values` 中的 `null`、缺失、类型错误和非有限数会转成字段级 422。
- 城市本期只校验非空和最多 30 字，不做生活模块的 44 城白名单。

## 响应

- `mode` 固定为 `backend`。
- `plan_input` 为 camelCase 基础字段；`result` 字段与前端 `PlanResult` 一致；`scenarios` 恰好三个。
- `explanation` 是规则文本；`warnings` 是字符串数组。

错误形状：

- 409 `SCHEMA_VERSION_MISMATCH`：`template_id` 或 `schema_version` 不符。
- 422 `VALIDATION_ERROR`：`{code, message, field_errors}`，`field` 用 `values` 的 snake_case 名。
- 500 `CALCULATION_ERROR`：未预期异常，不返回堆栈。

## 测试

```bash
cd src
uv run pytest tests/test_api_plan.py tests/test_pages.py
uv run ruff check api plan pages tests
```

接口测试直接读取 `frontend/contracts/` 的请求与响应示例，覆盖 200、409、422、非法 JSON、未知顶层字段和自定义城市；页面清单测试对比 `tests/fixtures/retirement-page.json`。
