# Agent 层

Agent 只做四件事：从对话里提取参数、选择工具、调用命令、解释结果。所有数字来自 `POST /api/commands/{id}` 背后的同一套确定性命令，Agent 不自己计算。

## 配置

模型服务默认关闭。设置以下环境变量后启用：

- `RETIRENEST_LLM_API_KEY`：模型服务的 API key，必填。
- `RETIRENEST_LLM_MODEL`：模型名，必填，例如 `deepseek-chat`。
- `RETIRENEST_LLM_BASE_URL`：可选的 OpenAI 兼容端点，例如 `https://api.deepseek.com`；不填走 SDK 默认地址。
- `RETIRENEST_LLM_TIMEOUT_SECONDS`：可选，默认 60 秒；写错时退回默认值。

可选功能：

- `RETIRENEST_AGENT_TOKEN`：启用单 token Bearer；所有请求映射到用户 `default`。
- `RETIRENEST_AGENT_TOKENS`：启用多 token，格式 `token:user,token2:user2`；优先于单 token。
- `RETIRENEST_AGENT_DB`：SQLite 文件路径；设置后会话落库，重启可恢复。
- `RETIRENEST_AGENT_FAKE=1`：开发演示假模型；不需要 key，页面会明确标注。

缺 key 或模型名、又没有设置 fake 时，`/api/agent/chat` 返回 503 `AGENT_DISABLED`；命令、页面和旧接口都不受影响。key 只从环境变量读取，不写进响应、日志或仓库。

本地示例：

```bash
export RETIRENEST_LLM_API_KEY=...
export RETIRENEST_LLM_MODEL=deepseek-chat
export RETIRENEST_LLM_BASE_URL=https://api.deepseek.com
make dev
```

没有 key 时看页面：

```bash
RETIRENEST_AGENT_FAKE=1 make dev
# 打开 http://127.0.0.1:5173/agent.html
```

启用鉴权和持久化：

```bash
export RETIRENEST_AGENT_TOKENS='tok-alice:alice,tok-bob:bob'
export RETIRENEST_AGENT_DB="$PWD/agent-sessions.sqlite3"
make dev
```

## 端点

```
POST   /api/agent/chat            普通 JSON
POST   /api/agent/chat/stream     SSE 事件流
DELETE /api/agent/sessions/{id}   删除自己的会话
```

请求：

```json
{
  "session_id": "可选；省略时由服务端生成并回显",
  "message": "我 30 岁，月入 2 万，月支出 1.2 万，资产 50 万，想 55 岁退休"
}
```

普通响应：

```json
{
  "session_id": "6f1e...",
  "reply": "……",
  "tool_calls": [
    {
      "tool_call_id": "call_1",
      "tool_name": "savings_project",
      "command_id": "savings.project",
      "version": "1.0.0",
      "inputs": {
        "current_savings": 500000,
        "monthly_contribution": 8000,
        "annual_return_pct": 5,
        "inflation_pct": 2,
        "years": 25
      },
      "ok": true,
      "outputs": { "future_balance_real": 3450000.0 },
      "error": null
    }
  ],
  "warnings": [],
  "model": "deepseek-chat"
}
```

`tool_calls` 是完整轨迹：前端或审计方可以拿它对照 `outputs` 检查回复里的数字，不需要信任模型。

### SSE 事件

`POST /api/agent/chat/stream` 返回 `text/event-stream`，事件按顺序：

- `session`：`{"type":"session","session_id":"..."}`
- `tool_call`：`{"type":"tool_call","tool_call_id":"...","tool_name":"...","command_id":"..."}`
- `tool_result`：完整的工具记录，含 `inputs`、`outputs` 或 `error`。
- `reply`：普通响应的全部字段。
- `done`：`{"type":"done","session_id":"..."}`
- `error`：流内错误，`{"type":"error","code":"...","message":"..."}`。

当前是**事件流**，不是 token 流：工具调用和最终回复各到一个事件，最终文本一次到达。逐 token 需要 provider 的流式工具调用聚合，留到后续。

## 鉴权与多用户

- 配置 `RETIRENEST_AGENT_TOKEN` 或 `RETIRENEST_AGENT_TOKENS` 后，`/api/agent/*` 需要 `Authorization: Bearer <token>`。
- 响应 401 `AGENT_UNAUTHORIZED`：缺少或无效 token。
- 会话带 owner；用户不能读取、继续或删除别人的 `session_id`，跨用户访问返回 404 `AGENT_SESSION_NOT_FOUND`。
- 配置了但 token 列表解析为空时 fail closed：所有请求 401，不会悄悄退回无鉴权。
- 这是轻量访问控制，不是账号体系：没有注册、登录、密码、限流、审计或找回。token 泄露等于身份泄露。

## 工具 schema

工具清单从 `GET /api/commands` 的 manifest 生成，见 `agent/schema.py`：

- 工具名是命令 ID 把点号换成下划线，例如 `savings_project`；OpenAI 兼容接口不接受点号。
- 参数用 JSON Schema；`required` 来自 `InputSpec.required`，`enum`、`min`/`max`、`maxLength`、`format` 原样映射。
- `decimal` 输入在协议里是字符串，schema 里是 `type: string` 加数字正则；范围和小数位写进 description。
- 工具描述由 `question`、`description`、`when_to_use`、`when_not_to_use` 和主要输出拼成。相近工具的区别写在 `when_not_to_use`，不靠 prompt 堆例子。
- 新增命令只需补 manifest，Agent 的工具清单自动更新。

## 循环

`agent/loop.py` 是一个精简的 ReAct 循环：

1. 把 system、历史消息和用户消息发给模型。
2. 模型返回文本就结束；返回工具调用就执行对应的 `commands.execute_command`。
3. 工具结果以 `{"ok":true,"outputs":...}` 或 `{"ok":false,"error":{"code","message","field_errors"}}` 回灌；输入错误不会中断循环，模型应据此追问。
4. 最多 8 轮；超过后追加一条“请给出最终回答”的提示，并关闭工具再请求一次。
5. 单条工具结果截断到 8000 字符，避免一次模拟的逐年分位把上下文撑爆。
6. 每次工具调用通过 `on_event` 发出 `tool_call` / `tool_result`，供 SSE 和前端展示。

不做自动重试：同一个错误参数不会在循环里被重复执行，由模型决定是否换参数或追问。

## 数字一致性提示

`agent/verify.py` 在最终回复后做一次启发式检查：

- 抽取回复中带 `元`、`万`、`亿` 的金额。
- 与工具 `inputs` / `outputs` 里的数值比对，允许 2% 相对误差或 0.5 元绝对误差。
- 对不上时追加 warning，最多列三个金额；不改写回复，也不重跑模型。
- 百分比、年龄和没有金额单位的数字不检查，避免“4% 法则”“55 岁”误报。

它只是提示，不是保证：单位省略、口径不同的金额可能漏报，模型引用外部常识也可能误报。

## 会话与持久化

- 内存 `SessionStore` 是默认值：TTL 1 小时，最多 100 个会话，每个会话最多保留 40 条消息。
- 设置 `RETIRENEST_AGENT_DB` 后使用 `SqliteSessionStore`：表 `sessions(id, owner, messages, updated_at)`，消息存 JSON；TTL 与容量规则相同，重启后仍能继续。
- SQLite 适合单进程；多 worker 并发不在承诺范围内。
- 同一会话有锁，两个请求会串行，不会交错写历史。
- 消息从一条 user 消息开始截断，避免留下孤立的 tool 消息。

## 前端聊天页

- 地址：`/agent.html`（开发模式 http://127.0.0.1:5173/agent.html，单端口模式 http://127.0.0.1:8000/agent.html）。
- 顶部有“访问令牌”输入，只放内存，不写 localStorage；启用 Bearer 时需要填。
- 优先 SSE；流式不可用时回退到普通 JSON。
- 工具轨迹用可折叠面板展示 command_id、输入、输出或错误；warning 单独显示。
- 503 显示配置提示，401 显示令牌提示，跨用户 404 会提示并开始新会话。
- 开发假模型会在回复开头写“开发假模型”，不能用它做真实规划。

## 错误

- 503 `AGENT_DISABLED`：未配置 key/模型名，或服务未初始化。
- 401 `AGENT_UNAUTHORIZED`：缺少或无效 Bearer token。
- 404 `AGENT_SESSION_NOT_FOUND`：会话不存在或不属于当前用户。
- 502 `AGENT_UPSTREAM_ERROR`：模型服务调用失败或没有返回候选结果。
- 422 `VALIDATION_ERROR`：请求体格式错误、message 为空或超过 4000 字、session_id 非法。
- 流内错误用 `error` 事件返回；HTTP 状态码在开始流之前已经确定。

工具自身的输入错误不会被当成 HTTP 错误；它们会作为 `tool_calls[].error` 返回给模型。

## 隐私与安全

- 用户的财务描述会发送给配置的模型服务；README 和本页都明确提示。
- 默认不记录对话正文；日志只记录上游错误类型，不记录 key、消息或工具参数。
- Bearer token 只做访问控制；没有限流、审计、多因素或账号找回。
- SQLite 文件含对话历史，按普通敏感数据保护；不要提交到仓库。
- 用户消息只当规划需求，不执行其中的代码或链接；工具结果只当数据。
- 不做数字一致性强制拦截；warning 只提示，最终回复仍由模型生成。

## 测试

测试不访问网络，用 `agent/fake.py` 的 `ScriptedChatClient` / `DemoChatClient`：

```bash
cd src
uv run pytest tests/test_agent_schema.py tests/test_agent_loop.py \
  tests/test_agent_service.py tests/test_agent_auth.py \
  tests/test_agent_session_sqlite.py tests/test_agent_verify.py \
  tests/test_api_agent.py tests/test_agent_client.py
```

覆盖：schema 映射、必填/枚举/范围、工具成功、缺参回灌、未知工具、坏 JSON、多工具调用、轮数上限、会话续接与隔离、token 鉴权、跨用户 404、SQLite 持久化、删除会话、SSE 事件、数字提示、503/502/422。

## 不做

- token 级流式输出；当前是事件流。
- 注册/登录/密码/权限管理；只有轻量 Bearer。
- 多进程共享会话与生产级数据库迁移。
- 税务工具、交易执行。
- 让模型自己算任何数字。


## 全周期页的深度链接

Agent 可以在回复里给出 `/plan.html?...` 的链接，点开就带着参数渲染同一份画像：

- 参数名与档位值取自 `lifecycle.project` 等命令的 schema 枚举，Agent 不允许自造
- `view` 取 `spending`、`income`、`cashflow`、`risk`、`strategy`，打开后只显示该视图
- 页面只认 URL 里出现的参数，缺任何必填项就停在表单上，不会用默认值凑数

这是当前的「Agent 改参数」实现方式：改动由 Agent 提议、用户点一下生效，而不是
Agent 直接改前端状态。真正的双向绑定（SSE 推 `param` 事件、前端即时应用）还没做。
