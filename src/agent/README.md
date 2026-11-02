# agent：LLM 编排层

LLM 只负责提取参数、选工具、调用命令和解释结果；所有数字来自 `commands.execute_command`。

## 文件

- `config.py`：`LLMConfig`，只从环境变量读取 key、模型名、base_url 与超时。
- `schema.py`：命令 manifest 转 OpenAI 兼容工具 schema；工具名把点号换成下划线。
- `prompt.py`：固定规则 + 从 manifest 生成的工具清单。
- `loop.py`：ReAct 循环，执行工具、回灌结果、轮数上限、截断。
- `session.py`：内存会话、TTL、容量上限、会话级锁。
- `service.py`：`AgentService`，组装 system prompt、历史和循环，维护会话。
- `client.py`：`OpenAIChatClient`，只依赖 chat.completions 兼容接口。
- `fake.py`：`ScriptedChatClient`，测试和本地接线用，不是 LLM。
- `models.py`：`ToolCall`、`AssistantTurn`、`ToolSpec`、`ToolCatalog`、`AgentRun`、`AgentReply`。
- `errors.py`：`AgentDisabled`、`AgentUpstreamError`。

## 约定

- 工具错误不抛 HTTP 500；转成 `{"ok":false,"error":{...}}` 回灌给模型，让模型追问。
- 工具结果截断到 8000 字符；完整结果在响应的 `tool_calls[].outputs` 里。
- 会话消息最多 40 条，从一条 user 消息开始截断，避免孤立 tool 消息。
- 未配置 key 或模型名时 Agent 关闭，其它端点不受影响。
- 不记录对话正文；日志只记录工具 ID 与错误类型。

## 测试

```bash
cd src
uv run pytest tests/test_agent_schema.py tests/test_agent_loop.py \
  tests/test_agent_service.py tests/test_api_agent.py
```

所有测试用假模型，不访问网络。
