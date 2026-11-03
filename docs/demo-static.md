# 静态体验包（GitHub Pages）

## 为什么要做

比赛表单要一条「项目体验」链接。Pages 只能托管静态文件，FastAPI 起不来，所以把引擎搬进浏览器：Pyodide 把 CPython 编译成 WebAssembly，页面里直接 `import` 仓库里那份 Python，算出来的数字与本地完全一致。

不移植成 JS 的原因很简单：口径只能有一份。抄一份计算逻辑，两次改动之后页面上的数字就会和 README 分叉。

线上地址：`https://zkazure.github.io/RetireNest/`，由本仓库的 `.github/workflows/pages.yml` 构建并发布。

## 四个部件

- `src/tools/build_demo_engine.py` — 打包引擎。把 `commands`、`pages`、`lifecycle` 等 15 个包与一个 `demo_bridge.py` 压成 `frontend/public/demo/py/engine.zip`（约 105 KB，83 个模块），排除依赖 fastapi 与 openai 的 `api/`、`agent/`。
- `frontend/src/pyodide-engine.ts` — 浏览器运行时。从 jsdelivr 懒加载 Pyodide 0.27.7，解包到 `/engine`，把 `page_json()` 与 `run_json()` 转成 Promise。
- `frontend/src/demo-shim.ts` — 拦截 `/api`：优先交给引擎，引擎起不来则退回预生成夹具（只读三个场景）。
- `frontend/vite.demo.config.ts` — `base` 为 `/RetireNest/`，产物落 `dist-demo/`，只打首页。

`npm run build:demo` 会先跑 `prebuild:demo`（即打包脚本）再构建，两者不会脱节。默认构建 `npm run build` 与这套东西无关。

## 两条路径

正常情况：引擎加载成功，表单可自由填写，任意字段改完点「开始测算」即重算，五类视图、策略对比、两页 PDF 都在浏览器里出。

兜底情况：CDN 不通或引擎初始化失败，`decide()` 切到 `fallback`，页面退回三个预置画像（60 / 55 / 63 岁），表单锁定、横幅说明原因。夹具由 `src/tools/build_demo_fixtures.py` 生成，`src/tests/test_demo_fixtures.py` 钉住它不过期。

## 重新生成

改了引擎代码（`src/` 下的领域模块）后，`npm run build:demo` 会自动重新打包，无需手工操作。

只有兜底夹具需要手动重跑：

```bash
cd src && uv run python tools/build_demo_fixtures.py
```

## 本地预览

`base` 是 `/RetireNest/`，直接开 `dist-demo` 里的 index.html 会丢样式，要放在同名目录下用静态服务器看：

```bash
cd frontend && npm run build:demo
mkdir -p /tmp/pages && rm -rf /tmp/pages/RetireNest
cp -r dist-demo /tmp/pages/RetireNest
cd /tmp/pages && python3 -m http.server 8099
# 打开 http://127.0.0.1:8099/RetireNest/
```

## 发布

`.github/workflows/pages.yml` 在 main 上构建 `dist-demo` 并部署。首次启用要去仓库 **Settings → Pages** 把 Source 选成「GitHub Actions」，之后推送 main 即自动上线。

## 边界

- 首次加载约 10 MB（Pyodide 运行时），之后走浏览器缓存；弱网用户会等几秒。
- `strategy.compare` 在 WASM 里约 1 到 3 秒，本机直算是 0.54 秒。
- 站点依赖 jsdelivr 可达。要彻底脱网，可把 Pyodide 静态文件自托管到本仓库，留作后续。
- 对话悬浮框在体验版里被移除：没有模型密钥与后端，留着会误导。
- 除了引擎与夹具，页面不发任何网络请求。
