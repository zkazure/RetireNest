# api：退休规划 HTTP 接入层

FastAPI 暴露以下端点：

- `GET /api/pages/{page_id}`：返回页面清单，主页据此渲染表单并决定提交时执行哪些命令。
- `GET /api/commands`：返回协议版本和十一个领域命令的 manifest。
- `POST /api/commands/{command_id}`：执行单个命令，请求 `{version, inputs}`，返回 `{command_id, version, outputs, meta}`。
- `POST /api/agent/chat`：Agent 对话端点，请求 `{session_id?, message}`；未配置模型服务时返回 503 `AGENT_DISABLED`，其它端点不受影响。
- `POST /api/agent/chat/stream`：同一对话的 SSE 事件流（`session`、`tool_call`、`tool_result`、`reply`、`done`、`error`）。
- `DELETE /api/agent/sessions/{id}`：删除当前用户的会话；跨用户返回 404。
- Agent 的可选配置：`RETIRENEST_AGENT_TOKEN(S)` 启用 Bearer，`RETIRENEST_AGENT_DB` 启用 SQLite，`RETIRENEST_AGENT_FAKE=1` 启用开发假模型。细节见 [docs/agent.md](../../docs/agent.md)。
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
- 503 `AGENT_DISABLED`：`/api/agent/*` 未配置模型服务；其它端点不受影响。
- 502 `AGENT_UPSTREAM_ERROR`：`/api/agent/*` 的模型服务调用失败。
- 401 `AGENT_UNAUTHORIZED`：启用了 Bearer 但缺少或提供了错误 token。
- 404 `AGENT_SESSION_NOT_FOUND`：会话不存在，或不属于当前 token 对应的用户。
- Agent 请求体的 422 仍走 FastAPI 的 `VALIDATION_ERROR`（`field_errors` 为空）；SSE 开始后的错误用 `error` 事件返回。

## 测试

```bash
cd src
uv run pytest tests/test_api_plan.py tests/test_pages.py
uv run ruff check api plan pages tests
```

接口测试直接读取 `frontend/contracts/` 的请求与响应示例，覆盖 200、409、422、非法 JSON、未知顶层字段和自定义城市；页面清单测试对比 `tests/fixtures/retirement-page.json`。
