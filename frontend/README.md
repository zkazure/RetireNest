# RetireNest 前端

HTML + CSS + 原生 TypeScript，使用 Vite 开发和构建，不依赖 UI 框架或外部字体。

## 一键启动

在仓库根目录执行：

```bash
uv run --project src python run.py
```

会启动 FastAPI（8000）和 Vite（5173），保留热更新，并自动打开 http://127.0.0.1:5173/。首次运行会自动安装依赖。

演示模式（单端口 8000，不需要 Vite）：

```bash
uv run --project src python run.py --prod
```

无桌面环境加 `--no-open`；Ctrl+C 会停止本次启动的所有进程。

## 命令浏览器

退休主页之外，另有一个开发者工具页面：

- 开发模式：http://127.0.0.1:5173/commands.html
- 单端口模式：http://127.0.0.1:8000/commands.html

页面从 `GET /api/commands` 读取 manifest，自动生成输入表单；“填充示例”写入 manifest 的第一条示例，“清空”回到默认值。执行 `POST /api/commands/{id}` 后先按 `outputs` 渲染输出表（只列 `visible !== false`，`decimal` 原样、数组与对象只做摘要），完整响应折叠在“原始 JSON”里。必填与 `required_when` 同步到原生校验，校验不过不发请求；后端 422 仍按字段展示。它只服务于命令调试，不做页面级组合；退休主页独立按页面清单执行。

前端用 `src/command-registry.ts` 的显式允许列表决定暴露哪些命令；后台新增命令不会自动出现。协议见 [../docs/command-protocol.md](../docs/command-protocol.md)。

## 规划对话（右下角悬浮框）

对话不是独立页面，而是全站右下角的悬浮气泡，点开是一个不离开当前页面的面板。

- 开发模式：http://127.0.0.1:5173/ ，点右下角气泡
- 单端口模式：http://127.0.0.1:8000/ ，点右下角气泡

面板用 `fetch` 调 `POST /api/agent/chat/stream`，边读 SSE 边渲染：`session` 忽略、`tool_call` 显示成「正在调用 …」的提示、`tool_result` 不展示、`reply` 落到气泡里、`warnings` 逐条附在后面、`error` 直接显示错误文案。没有流式响应时，503 会被换成一句「去模型设置填写」的引导。

模型密钥在 `/settings.html` 里填，存当前浏览器的 localStorage，发消息时随 `X-LLM-Api-Key`、`X-LLM-Model`、`X-LLM-Base-Url` 请求头带给后端。**页面 origin 与填设置的 origin 必须一致**：`localhost` 与 `127.0.0.1`、5173 与 8000 都算不同 origin，localStorage 不互通。服务端配了环境变量时可以不填；配了 Bearer 时设置页的访问令牌也一样只放 localStorage。Agent 配置、鉴权、SQLite 与会话说明见 [../docs/agent.md](../docs/agent.md)，起服务的完整流程见 [../.agents/skills/start-retirenest/SKILL.md](../.agents/skills/start-retirenest/SKILL.md)。

## 手动启动（排错）

先启动后端（见 [../src/api/README.md](../src/api/README.md)），再在 frontend 目录执行：

```bash
npm install
npm run dev
```

浏览器打开终端中显示的本地地址（默认 http://127.0.0.1:5173）。开发期 Vite 把 `/api` 代理到 `http://127.0.0.1:8000`，见 `vite.config.ts`。

```bash
npm run build
npm run preview
```

build 同时执行 TypeScript 严格检查和生产构建，静态产物位于 dist/。preview 也配置了同样的 `/api` 代理。

## 当前功能

- 基本信息、收支、资产负债、退休目标、回报及通胀假设表单。
- 退休资金目标、预计资产、资金缺口、准备度和月结余目标。
- SVG 资产曲线、退休节点、目标线、资产不足年龄。
- 保守 / 基准 / 乐观情景，由后端返回，名义回报分别为用户输入 −1 / 不变 / +1 个百分点，限制在输入范围内。
- 后端字段级错误回填、测算说明弹窗、PDF 报告导出。
- 桌面 / 平板 / 手机响应式布局。

启动时播放可跳过的 slogan 动画，开启系统减少动画偏好时直接进入。页首保留品牌，仅在结果页显示导出按钮，初始仅展示填写卡片。城市从后端提供的 44 城列表中选择。点击“生成我的退休规划”且校验成功后，隐藏填写卡片，请求与约 1.8 秒的三阶段过渡动画并行；成功后淡出 400 毫秒再展示结果，失败则回到表单并显示错误。点击“返回修改”或“调整我的规划”可返回，填写内容保留。生成前、生成过程中和返回编辑时隐藏导出按钮，避免导出未确认的草稿。切换情景卡片只更新该情景说明，不替换基准图表。内容不在浏览器持久化，刷新后恢复示例；提交时只会发送到本地后端，不保存。

## 与后端对接

- `src/page-client.ts`：`GET /api/pages/retirement`，20 秒超时，校验页面清单结构。
- `src/page-types.ts`、`src/page-to-template.ts`：页面清单类型，以及到通用表单结构的转换。
- `src/page-values.ts`、`src/page-runner.ts`：按执行清单取值、逐个调用 `POST /api/commands/{id}` 并合并字段错误。
- `src/plan-adapter.ts`：把 `plan.retirement` 的输出映射成结果页使用的 `PlanResponse`。
- `src/module-results.ts`：按命令的输出规格渲染模块结果卡片。
- `src/plan-contract.ts`：`PlanResponse`、`PlanScenario` 类型。
- `src/command-types.ts`、`src/command-client.ts`：命令清单与单命令执行类型/客户端。
- `src/command-registry.ts`：前端显式注册表，决定哪些命令进入命令浏览器。
- `src/command-browser.ts`、`commands.html`：通用命令浏览器。
- `src/command-output.ts`：命令浏览器的输出表，按 `outputs` 规格过滤与格式化。
- `src/agent-chat.ts`、`agent.html`、`src/agent-chat.css`：规划对话页。
- `src/agent-stream.ts`：增量 SSE 解析器。
- `src/model.ts`：只保留 `PlanInput`、`ProjectionPoint`、`PlanResult` 类型，不再本地计算。
- `src/main.ts`：表单事件、页面加载、结果渲染、字段级错误和 PDF 入口。
- `src/pdf-export.ts`：接收后端返回的 `plan_input`、`result`、`scenarios` 和 `explanation`。
- `vite.config.ts`：开发期与 preview 的 `/api` 代理。

PlanInput 金额单位是元；nominalReturn 和 inflation 是百分数（3 表示 3%）；coverage 也是百分数（80 表示 80%）。points[].assets、target、projected 和 gap 的单位均为元。depletedAge 为首次在退休期出现负资产的年龄，未出现则为 null。

底部“规则解读”仍由后端的规则文本生成，不是 LLM 输出；对话页的回复才来自 Agent。模型密钥只放后端环境变量，绝不要放进前端。配置见 [../docs/agent.md](../docs/agent.md)。

## 测算口径

全部金额用今天的购买力表示。实际回报率 = (1 + 名义回报率) / (1 + 通胀率) − 1。假设工资、支出和养老金随通胀同步变化，实际金额保持不变。

当前净资产 = 总资产 − 总负债；月结余 = 收入 − 支出。工作期每年年末计入 12 个月结余；退休后每年年末支取 max(退休月支出 − 月养老金, 0) × 12。养老金视为退休起持续领取的用户假设。全周期页已改为逐年滚动：收入 = 工资 + 养老金 + 资产收益，退休后工资归零；资产收益 = 期初资产 × 组合实际收益率，口径见 [../docs/data-sources.md](../docs/data-sources.md) 2.5 节。

目标资金为退休后各年净支出的现值；预计资产为当前净资产和未来结余在退休时的累积值。负债直接抵减资产，不另算利息；不计税费、回报波动、社保政策。城市只展示，不影响计算。负资产会在图上继续呈现，用于暴露缺口。

结果仅供比赛演示和学习，不是投资建议或真实养老金测算。

## 接口与提示动画

提交时只发送页面清单里声明的命令参数，不包含任意 DOM 控件或密钥。请求进行期间显示生成面板，失败时在表单顶部展示后端消息，命令返回的 `field_errors` 会定位到对应输入框。

提示栏以 350ms 从底部升入，显示约 3.2 秒后以 300ms 淡出。连续提示会取消旧的退出定时器。减少动画偏好下直接切换。

## PDF 报告导出

结果页点击“导出规划”直接下载两页 A4 PDF，内容包括规划概览、输入信息、资产曲线、三种情景、规则解读及测算假设。使用后端已返回的结果，不读取正在编辑的草稿。导出期间按钮禁用并显示生成状态，失败可重试。

实现位于 src/pdf-export.ts，pdf-lib 通过动态导入按需加载。中文使用浏览器本机字体在 2 倍分辨率 Canvas 绘制，再嵌入 PDF；报告是图像页面，文本暂不支持选择、搜索。导出只在浏览器本地生成，不再发请求。

## 页面清单驱动

填写栏不再由前端配置。启动时请求 `GET /api/pages/retirement`，字段的问题文案、类型、单位、选项、约束、分组、开关和跨字段规则都来自后端；前端只做结构转换和渲染。

提交时按页面清单的执行清单逐个调用命令：`plan.retirement` 与 `living.calculate` 总是执行，医疗、养老金、存款按分组开关执行。任一命令失败即回到表单并合并所有 `field_errors`；结果页先展示退休规划，再按命令输出渲染模块卡片。

字段约束是后端算出来的：同一字段被多个命令消费时取交集，前端不持有范围数字。城市列表来自 `living.calculate` 的 44 城枚举，不再支持自定义城市。

执行 npm test 验证页面清单到表单的映射、执行清单取值和规则校验。
