# api：退休规划 HTTP 接入层

FastAPI 提供 `POST /api/retirement/plan`，把前端动态表单的 `values` 映射成 12 个基础字段，调用 `plan` 包计算，返回与 `frontend/contracts/plan-response.example.json` 同构的响应。

## 启动

```bash
cd src
uv sync
uv run uvicorn api.app:app --host 127.0.0.1 --port 8000
```

前端开发服务器通过 `/api` 代理访问这里，见 `frontend/vite.config.ts`；本层不开启 CORS。

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

- 只读取 12 个基础字段；医疗、养老、存款、生活偏好等扩展字段静默忽略，保证 43 字段的模板请求仍可用。
- `values` 中的 `null`、缺失、类型错误和非有限数会转成字段级 422。
- 城市本期只校验非空和最多 30 字，不做现有生活模块的 44 城白名单。

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
uv run pytest tests/test_api_plan.py
uv run ruff check api plan tests/test_api_plan.py tests/test_plan_engine.py
```

接口测试直接读取 `frontend/contracts/` 的请求与响应示例，覆盖 200、409、422、非法 JSON、未知顶层字段和自定义城市。
