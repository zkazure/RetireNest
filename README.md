# RetireNest

“退有所算”是一个面向个人的退休财务规划智能体。
用户输入居住城市、年龄、收入、资产、负债、期望退休年龄与生活水平后，智能体结合地区生活成本、通胀、预期寿命和社保养老金假设，测算退休所需存款、当前缺口、建议储蓄率，并给出多情景对比。
系统采用“确定性计算引擎 + LLM 对话收集与解释 + 前端可视化”的架构，所有关键数字可追溯、可复核，帮助用户从“凭感觉焦虑”转向“按数字行动”。

## 目录

代码在 `src/` 下，每个目录的用途见 [src/INDEX.md](src/INDEX.md)。

## 前端预览

前端位于 `frontend/`，采用 HTML + CSS + TypeScript，使用 Vite。

```powershell
cd frontend
npm install
npm run dev
```

默认访问 http://127.0.0.1:5173/。运行 `npm run build` 执行类型检查和生产构建。

已实现规划信息表单、退休资金概览、资产曲线、三种情景对比、规则解读与 PDF 报告导出。目前使用本地演示计算，未接入后端和 LLM。运行方法、计算口径与接口接入说明见 [frontend/README.md](frontend/README.md)。

前端填写栏已支持动态 JSON 模板。后端对接以 [frontend/FORM_TEMPLATE.md](frontend/FORM_TEMPLATE.md) 及 frontend/contracts/ 中的示例为准。
