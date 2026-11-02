# RetireNest

“退有所算”是一个面向个人的退休财务规划智能体。
用户输入居住城市、年龄、收入、资产、负债、期望退休年龄与生活水平后，智能体结合地区生活成本、通胀、预期寿命和社保养老金假设，测算退休所需存款、当前缺口、建议储蓄率，并给出多情景对比。
系统采用“确定性计算引擎 + LLM 对话收集与解释 + 前端可视化”的架构，所有关键数字可追溯、可复核，帮助用户从“凭感觉焦虑”转向“按数字行动”。

## 目录

代码在 `src/` 下，每个目录的用途见 [src/INDEX.md](src/INDEX.md)。

## 本地运行

先启动后端，再启动前端。开发期由 Vite 把 `/api` 代理到 `127.0.0.1:8000`。

```bash
cd src
uv sync
uv run uvicorn api.app:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

默认访问 http://127.0.0.1:5173/。运行 `npm run build` 执行类型检查和生产构建。

已实现规划信息表单、退休资金概览、资产曲线、三种情景对比、规则解读与 PDF 报告导出。基础 12 个字段已接入本地 FastAPI 后端；医疗、养老、存款等扩展信息仍只收集，尚未参与计算；LLM 未接入。运行方法、计算口径与接口说明见 [frontend/README.md](frontend/README.md) 和 [src/api/README.md](src/api/README.md)。

前端填写栏已支持动态 JSON 模板。接口契约以 [frontend/FORM_TEMPLATE.md](frontend/FORM_TEMPLATE.md) 及 `frontend/contracts/` 中的示例为准。
