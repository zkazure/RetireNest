# agent：LLM 编排层

LLM 只负责提取参数、选工具、调用命令和解释结果；所有数字来自 `commands.execute_command`。

## 文件

- `config.py`：`LLMConfig`，只从环境变量读取 key、模型名、base_url 与超时。
- `auth.py`：`AgentAuth`，单 token 或 `token:user` 映射；配置了但为空时 fail closed。
- `schema.py`：命令 manifest 转 OpenAI 兼容工具 schema；工具名把点号换成下划线。
- `prompt.py`：固定规则 + 从 manifest 生成的工具清单。
- `loop.py`：ReAct 循环，执行工具、回灌结果、轮数上限、截断、SSE 事件回调。
- `verify.py`：回复中的金额与工具输入/输出比对，对不上时追加 warning。
- `session.py`：内存与 SQLite 会话、TTL、容量上限、owner 隔离、会话级锁。
- `service.py`：`AgentService`，组装 system prompt、历史和循环，维护会话。
- `client.py`：`OpenAIChatClient`，只依赖 chat.completions 兼容接口。
- `fake.py`：`ScriptedChatClient` 测试用；`DemoChatClient` 无 key 时看界面用，不是 LLM。
- `models.py`：`ToolCall`、`AssistantTurn`、`ToolSpec`、`ToolCatalog`、`AgentRun`、`AgentReply`。
- `errors.py`：`AgentDisabled`、`AgentUnauthorized`、`AgentSessionNotFound`、`AgentUpstreamError`。

## 配置

- `RETIRENEST_LLM_API_KEY` / `RETIRENEST_LLM_MODEL`：模型服务。
- `RETIRENEST_LLM_BASE_URL`：可选 OpenAI 兼容端点。
- `RETIRENEST_AGENT_TOKEN` / `RETIRENEST_AGENT_TOKENS`：可选 Bearer 鉴权。
- `RETIRENEST_AGENT_DB`：可选 SQLite 路径。
- `RETIRENEST_AGENT_FAKE=1`：开发演示假模型。

细节见 [docs/agent.md](../../docs/agent.md)。

## 约定

- 工具错误不抛 HTTP 500；转成 `{"ok":false,"error":{...}}` 回灌给模型，让模型追问。
- 工具结果截断到 8000 字符；完整结果在响应的 `tool_calls[].outputs` 里。
- 会话消息最多 40 条，从一条 user 消息开始截断，避免孤立 tool 消息。
- 会话按 owner 隔离；跨用户访问返回 404，不泄露会话是否存在。
- 未配置 key 或模型名时 Agent 关闭；`RETIRENEST_AGENT_FAKE=1` 可绕过模型服务做界面演示。
- 不记录对话正文；日志只记录工具 ID 与错误类型。

## 测试

```bash
cd src
uv run pytest tests/test_agent_schema.py tests/test_agent_loop.py \
  tests/test_agent_service.py tests/test_agent_auth.py \
  tests/test_agent_session_sqlite.py tests/test_agent_verify.py \
  tests/test_api_agent.py tests/test_agent_client.py
```

所有测试用假模型，不访问网络。
