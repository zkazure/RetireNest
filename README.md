# RetireNest

“退有所算”是一个面向个人的退休财务规划智能体。
用户输入居住城市、年龄、收入、资产、负债、期望退休年龄与生活水平后，智能体结合地区生活成本、通胀、预期寿命和社保养老金假设，测算退休所需存款、当前缺口、建议储蓄率，并给出多情景对比。
系统采用“确定性计算引擎 + LLM 对话收集与解释 + 前端可视化”的架构，所有关键数字可追溯、可复核，帮助用户从“凭感觉焦虑”转向“按数字行动”。

## 目录

代码在 `src/` 下，每个目录的用途见 [src/INDEX.md](src/INDEX.md)。

## 一条命令运行

前置工具：Python 3.12、[uv](https://docs.astral.sh/uv/)、Node.js（含 npm），以及 GNU make。首次运行会自动执行 `uv sync --locked` 和 `npm ci`，需要网络。

make 的安装：Linux 发行版通常自带；macOS 用 `xcode-select --install` 或 `brew install make`；Windows 用 `winget install ezwinports.make`，或 `choco install make`、`scoop install make`，装完重开终端。Windows 上 make 的 recipe 由 cmd.exe 执行，本项目只用最简单的命令，不需要 MSYS2。

开发模式（FastAPI 8000 + Vite 5173，保留热更新）：

```bash
make dev
```

`make dev` 会先结束占用 8000/5173 的旧进程再启动，Linux、macOS 与 Windows 行为一致，适合改完代码直接重启；`make stop` 只结束旧进程。跳过自动打开浏览器用 `make dev ARGS=--no-open`，演示模式用 `make dev ARGS=--prod`，只清理指定端口用 `make stop PORTS=18000`。

端口清理由 `run.py --stop` 实现：Windows 用 `netstat -ano` 找 PID 再 `taskkill /F /T`，Linux/macOS 用 `lsof`（缺失时退 `ss`）。Windows 这条路径由单元测试覆盖，尚未在 Windows 实机验证。

没有 make 时用等价写法：

```bash
uv run --project src python run.py
uv run --project src python run.py --stop
```

演示模式（构建前端后由 FastAPI 在 8000 单端口托管页面和 API）：

```bash
uv run --project src python run.py --prod
```

默认会自动打开浏览器：开发模式打开命令浏览器 `/commands.html`，演示模式打开主页。无桌面环境或远程服务器加 `--no-open`。Ctrl+C 会停止本次启动的所有进程。手动启动方式见 [frontend/README.md](frontend/README.md)。

命令浏览器（开发者工具）：

- 开发模式：http://127.0.0.1:5173/commands.html
- 单端口模式：http://127.0.0.1:8000/commands.html

规划对话页：

- 开发模式：http://127.0.0.1:5173/agent.html
- 单端口模式：http://127.0.0.1:8000/agent.html

命令清单由 `GET /api/commands` 提供，单个命令通过 `POST /api/commands/{id}` 执行；退休规划主页由 `GET /api/pages/retirement` 的页面清单驱动，提交时逐个调用命令。protocol、manifest、页面清单和错误格式见 [docs/command-protocol.md](docs/command-protocol.md)。`POST /api/retirement/plan` 保留为过渡接口。

已实现规划信息表单、退休资金概览、资产曲线、三种情景对比、规则解读与 PDF 报告导出。退休资金由 `plan.retirement` 命令计算；医疗、养老、存款与生活支出由各自命令独立测算并在结果页单独展示，不并入退休资金目标。

命令层另有六个计算原语：`savings.project`（储蓄增长）、`savings.goal`（目标倒推）、`inflation.convert`（通胀换算）、`simulation.retirement`（蒙特卡洛）、`withdrawal.safe_rate`（安全提取率）、`longevity.estimate`（Gompertz 寿命估计）。它们不进入主页表单，可在命令浏览器中单独执行，供 Agent 层调用；口径与 `plan.retirement` 一致，并有 `rel=1e-12` 的交叉校验。

Agent 层已接入但默认关闭：设置 `RETIRENEST_LLM_API_KEY` 与 `RETIRENEST_LLM_MODEL`（可选 `RETIRENEST_LLM_BASE_URL`）后，`/agent.html`、`POST /api/agent/chat` 与 SSE 端点可用；未配置时返回 503，命令、页面和旧接口都不受影响。没有 key 时可用 `RETIRENEST_AGENT_FAKE=1` 跑固定演示。可选 `RETIRENEST_AGENT_TOKEN(S)` 启用 Bearer 访问控制，`RETIRENEST_AGENT_DB` 启用 SQLite 会话持久化。配置、隐私、SSE 事件与错误说明见 [docs/agent.md](docs/agent.md)。

运行方法、计算口径与接口说明见 [frontend/README.md](frontend/README.md) 和 [src/api/README.md](src/api/README.md)。

前端不再保存字段配置：表单的问题、类型、选项、约束与分组全部来自后端页面清单。契约示例见 `frontend/contracts/`。
