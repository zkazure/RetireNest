# 静态体验包（GitHub Pages）

## 为什么要做

比赛表单要一条「项目体验」链接，而 GitHub Pages 只能托管静态文件，FastAPI 起不来。于是把页面清单与三条命令在若干预置画像上的输出，在构建期算成一份 JSON，浏览器里直接读，不依赖后端。

线上地址：`https://zkazure.github.io/RetireNest/`，由本仓库的 `.github/workflows/pages.yml` 构建并发布。

## 三个部件

- `src/tools/build_demo_fixtures.py` — 夹具生成器。改写退休年龄生成三个场景，跑 `lifecycle.project`、`lifecycle.simulate`、`strategy.compare`，把输出连同输入键写进 `frontend/public/demo/fixtures.json`。
- `frontend/src/demo-shim.ts` — 演示层。只在 `VITE_DEMO=true` 时安装，拦截 `/api` 请求喂夹具；锁死表单、隐藏命令浏览器与设置入口、移除对话悬浮框、加「静态演示」横幅，并在页面打开时自动套用第一个画像跑一次。
- `frontend/vite.demo.config.ts` — 演示构建。`base` 是 `/RetireNest/`，产物落 `dist-demo/`，只打首页。

默认构建 `npm run build` 与这套东西无关，`installDemoShim()` 在默认构建里是空操作。

## 重新生成

改了口径、画像或命令输出后，两步：

```bash
cd src && uv run python tools/build_demo_fixtures.py
cd ../frontend && npm run build:demo
```

夹具是快照，不重跑就会和线上数字对不上。`src/tests/test_demo_fixtures.py` 会拿「重新生成的结果」和「已提交的文件」比对，口径改了却没重跑时直接红。

## 发布

站点由本仓库直接发布：`.github/workflows/pages.yml` 在 main 上构建 `dist-demo`，再部署到 `https://zkazure.github.io/RetireNest/`。

首次启用要去仓库 **Settings → Pages**，把 Source 选成「GitHub Actions」。之后推送 main 即自动上线，不需要手工拷贝。

不另开博客仓库的原因：Pages 的地址由「哪个仓库开了 Pages」决定，本仓库名就是 `RetireNest`，开在这里路径天然是 `/RetireNest/`；产物与源码同库，改完一次推送就同步，不会出现两份产物互相漂移。

## 本地预览

`base` 是 `/RetireNest/`，直接开 `dist-demo` 里的 index.html 会丢样式，要放在同名目录下用静态服务器看：

```bash
cd frontend && npm run build:demo
mkdir -p /tmp/pages && rm -rf /tmp/pages/RetireNest
cp -r dist-demo /tmp/pages/RetireNest
cd /tmp/pages && python3 -m http.server 8099
# 打开 http://127.0.0.1:8099/RetireNest/
```

## 边界

- 只提供三个预置画像（奶龙 60 / 55 / 63 岁），只能切换、不能改数字。任意输入可算需要后端。
- 对话悬浮框在演示版里被移除：没有 `/api/agent` 后端，留着会误导。
- 静态版不发任何网络请求，除自身静态资源与夹具。
