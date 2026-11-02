# RetireNest

“退有所算”是一个面向个人的退休财务规划智能体。
用户输入居住城市、年龄、收入、资产、负债、期望退休年龄与生活水平后，智能体结合地区生活成本、通胀、预期寿命和社保养老金假设，测算退休所需存款、当前缺口、建议储蓄率，并给出多情景对比。
系统采用“确定性计算引擎 + LLM 对话收集与解释 + 前端可视化”的架构，所有关键数字可追溯、可复核，帮助用户从“凭感觉焦虑”转向“按数字行动”。

## 目录

代码在 `src/` 下，每个目录的用途见 [src/INDEX.md](src/INDEX.md)。

## 一条命令运行

前置工具：Python 3.12、[uv](https://docs.astral.sh/uv/)、Node.js（含 npm）。首次运行会自动执行 `uv sync --locked` 和 `npm ci`，需要网络。

开发模式（FastAPI 8000 + Vite 5173，保留热更新）：

```bash
uv run --project src python run.py
```

演示模式（构建前端后由 FastAPI 在 8000 单端口托管页面和 API）：

```bash
uv run --project src python run.py --prod
```

默认会自动打开浏览器；无桌面环境或远程服务器加 `--no-open`。Ctrl+C 会停止本次启动的所有进程。手动启动方式见 [frontend/README.md](frontend/README.md)。

命令浏览器（开发者工具）：

- 开发模式：http://127.0.0.1:5173/commands.html
- 单端口模式：http://127.0.0.1:8000/commands.html

命令清单由 `GET /api/commands` 提供，单个命令通过 `POST /api/commands/{id}` 执行；退休规划主页由 `GET /api/pages/retirement` 的页面清单驱动，提交时逐个调用命令。protocol、manifest、页面清单和错误格式见 [docs/command-protocol.md](docs/command-protocol.md)。`POST /api/retirement/plan` 保留为过渡接口。

已实现规划信息表单、退休资金概览、资产曲线、三种情景对比、规则解读与 PDF 报告导出。退休资金由 `plan.retirement` 命令计算；医疗、养老、存款与生活支出由各自命令独立测算并在结果页单独展示，不并入退休资金目标；LLM 未接入。运行方法、计算口径与接口说明见 [frontend/README.md](frontend/README.md) 和 [src/api/README.md](src/api/README.md)。

前端不再保存字段配置：表单的问题、类型、选项、约束与分组全部来自后端页面清单。契约示例见 `frontend/contracts/`。
