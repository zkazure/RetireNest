---
name: start-retirenest
description: 启动、重启、停止 RetireNest 本地服务并排查模型配置问题；说明开发与演示两种模式、8000/5173 两套入口、密钥来源优先级与验证命令。Use when asked to start, restart, or stop the RetireNest dev server, when ports 8000/5173 are involved, when the model API key or RETIRENEST_LLM_* variables need configuring, or when the agent returns 503 AGENT_DISABLED.
whenToUse: 用户说「启动 / 重启 / 跑起来 / 停一下 / 换个端口」，或遇到 503 AGENT_DISABLED、模型密钥不生效、页面与接口不同源。
---

# 启动 RetireNest

## 快速开始

```bash
make dev                 # 结束旧进程并启动：API 8000 + 页面 5173
make dev ARGS=--prod     # 先构建前端，再由 8000 单端口托管页面与 API
make stop                # 只结束监听 8000/5173 的进程
```

没有 make 时用等价命令：

```bash
uv run --project src python run.py
uv run --project src python run.py --prod --no-open
uv run --project src python run.py --stop --ports 8000 5173
```

不要直接用 `uvicorn` 启动：那样会跳过依赖同步与 `.env.local` 加载。装依赖只用 `uv add` / `uv sync`，依赖声明只写 `src/pyproject.toml`。

## 端口与两套入口

- 5173：Vite 开发服务器，页面在这里，`/api` 代理到 8000；开发时以它为准。
- 8000：FastAPI。开发模式下只要 `frontend/dist` 存在，它也会托管一份页面，于是 8000 成了第二个可访问的 origin，不是主入口。
- `--prod` 时只有 8000，Vite 不启动。

## 模型密钥

优先级从高到低：

1. 设置页（`/settings.html`，存 localStorage）填的 key，发消息时放进 `X-LLM-Api-Key` / `X-LLM-Model` / `X-LLM-Base-Url` 请求头，只作用于当轮请求。
2. 进程环境变量 `RETIRENEST_LLM_API_KEY` 与 `RETIRENEST_LLM_MODEL`（可选 `RETIRENEST_LLM_BASE_URL`、`RETIRENEST_LLM_TIMEOUT_SECONDS`）。`run.py` 启动时会把仓库根目录的 `.env.local` 补进进程环境，已存在的变量不覆盖。

`.env.local` 格式（该文件已被 gitignore）：

```bash
RETIRENEST_LLM_API_KEY=sk-...
RETIRENEST_LLM_MODEL=deepseek-chat
RETIRENEST_LLM_BASE_URL=https://api.deepseek.com/v1
```

- 需要临时换一套配置：在命令前 export，进程环境优先于文件。
- 只想看界面、不接模型：`RETIRENEST_AGENT_FAKE=1 make dev`。
- 密钥只留在 `.env.local` 或当次进程环境里，不要写进被跟踪的文件、README、commit message 或聊天回复，也不要 `echo` 出来。

## 验证

```bash
curl -s http://127.0.0.1:8000/api/agent/config
```

`configured.enabled` 为 true 且 `configured.missing` 为空，才算密钥生效。配置在服务导入时读取一次，改了环境变量或 `.env.local` 必须重启。

## 常见故障

- 503 且文案列出 `RETIRENEST_LLM_API_KEY、RETIRENEST_LLM_MODEL`：请求没带 key 头，进程里也没有这两个变量。
- 503 只列 `RETIRENEST_LLM_MODEL`：key 有了，模型名没给。
- 设置页填了仍 503：页面 origin 与填设置页的 origin 不同。localStorage 按 origin 隔离，`localhost` 与 `127.0.0.1` 也算不同 origin；在哪个端口聊天，就在那个端口的 `/settings.html` 重新填。
- 端口被占用：`make stop`，或用 `--stop --ports <端口>` 只清指定端口。
- 8000 上是旧页面：`frontend/dist` 是上次构建的产物，开发一律用 5173。

## 边界

- `--stop` 不读 `.env.local`；环境变量文件只在真正启动时加载。
- 项目没有 dotenv 依赖，`.env.local` 由 `run.py` 自己解析；不要为此新增依赖。
- 启动日志只打印补进去的变量名，不打印值；改这里时保持这一点。
