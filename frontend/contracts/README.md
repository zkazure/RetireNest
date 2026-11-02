# 契约示例

两组示例同时存在，对应两个入口：

- `command-plan-request.example.json`、`command-plan-response.example.json`：主页现在使用的 `POST /api/commands/plan.retirement` 请求与响应。
- `plan-request.example.json`、`plan-request-all-modules.example.json`、`plan-response.example.json`、`plan-error.example.json`：过渡接口 `POST /api/retirement/plan` 的示例，新前端不再调用，但后端测试仍用它做回归。

页面清单不在这里存副本：完整响应在 `src/tests/fixtures/retirement-page.json`，前后端测试共用同一份，避免各造数据。
