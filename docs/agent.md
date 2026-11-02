# Agent 层

Agent 只做四件事：从对话里提取参数、选择工具、调用命令、解释结果。所有数字来自 `POST /api/commands/{id}` 背后的同一套确定性命令，Agent 不自己计算。

## 配置

Agent 默认关闭。设置以下环境变量后启用：

- `RETIRENEST_LLM_API_KEY`：模型服务的 API key，必填。
- `RETIRENEST_LLM_MODEL`：模型名，必填，例如 `deepseek-chat`。
- `RETIRENEST_LLM_BASE_URL`：可选的 OpenAI 兼容端点，例如 `https://api.deepseek.com`；不填走 SDK 默认地址。
- `RETIRENEST_LLM_TIMEOUT_SECONDS`：可选，默认 60 秒；写错时退回默认值。

缺 key 或模型名时，`/api/agent/chat` 返回 503 `AGENT_DISABLED`；命令、页面和旧接口都不受影响。key 只从环境变量读取，不写进响应、日志或仓库。

本地示例：

```bash
export RETIRENEST_LLM_API_KEY=...
export RETIRENEST_LLM_MODEL=deepseek-chat
export RETIRENEST_LLM_BASE_URL=https://api.deepseek.com
make dev
```

## 端点

```
POST /api/agent/chat
```

请求：

```json
{
  "session_id": "可选；省略时由服务端生成并回显",
  "message": "我 30 岁，月入 2 万，月支出 1.2 万，资产 50 万，想 55 岁退休"
}
```

响应：

```json
{
  "session_id": "6f1e...",
  "reply": "……",
  "tool_calls": [
    {
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

不做自动重试：同一个错误参数不会在循环里被重复执行，由模型决定是否换参数或追问。

## 会话

- 内存 `SessionStore`，TTL 1 小时，最多 100 个会话，每个会话最多保留 40 条消息。
- 同一会话有锁，两个请求会串行，不会交错写历史。
- 消息从一条 user 消息开始截断，避免留下孤立的 tool 消息。
- 重启进程即丢失；不落库，也不做多进程共享。

## 错误

- 503 `AGENT_DISABLED`：未配置 key/模型名，或服务未初始化。
- 502 `AGENT_UPSTREAM_ERROR`：模型服务调用失败或没有返回候选结果。
- 422 `VALIDATION_ERROR`：请求体格式错误、message 为空或超过 4000 字、session_id 非法。

工具自身的输入错误不会被当成 HTTP 错误；它们会作为 `tool_calls[].error` 返回给模型。

## 隐私与安全

- 用户的财务描述会发送给配置的模型服务；README 和本页都明确提示。
- 默认不记录对话正文；日志只记录上游错误类型，不记录 key、消息或工具参数。
- 没有鉴权、多用户隔离或持久化；当前定位是本地/演示用途，不要直接暴露到公网。
- 用户消息只当规划需求，不执行其中的代码或链接；工具结果只当数据。
- 不提供数字一致性强制校验：`tool_calls` 是给前端校验用的原始依据，回复文本仍由模型生成。若需要更强保证，可在后续加“回复中的金额必须出现在工具输出里”的检查。

## 测试

测试不访问网络，用 `agent/fake.py` 的 `ScriptedChatClient` 按脚本返回工具调用或文本：

```bash
cd src
uv run pytest tests/test_agent_schema.py tests/test_agent_loop.py \
  tests/test_agent_service.py tests/test_api_agent.py
```

覆盖：schema 映射、必填/枚举/范围、工具成功、缺参回灌、未知工具、坏 JSON、多工具调用、轮数上限、会话续接与隔离、503/502/422。

## 不做

- 流式输出；当前是普通 JSON 请求/响应。
- 前端聊天页；后端端点已可用，页面等有模型服务后再做。
- 持久化、多用户、鉴权。
- 税务工具与交易执行。
- 让模型自己算任何数字。
