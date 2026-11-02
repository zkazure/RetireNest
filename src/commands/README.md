# commands：可发现的领域命令

`src/commands/` 把现有领域模块包装成命令：一份 manifest + 一个 `run` handler。HTTP 层只负责发现和执行，不决定页面结构。协议见 [docs/command-protocol.md](../../docs/command-protocol.md)。

## 当前命令

- `plan.retirement` → `plan` 包的 `validate` / `calculate` / `build_scenarios` / `build_explanation`
- `medical.estimate` → `medical.estimate_medical_cost`
- `pension.basic` → `pension.BasicPensionInput` / `pension.calculate`
- `deposit.demand` → `deposit.DemandDeposit` / `deposit.calculate`
- `living.calculate` → `living.calculate()`

## 文件

- `models.py`：`InputSpec`、`OutputSpec`、`CommandManifest`、`Command`。
- `validation.py`：按 manifest 校验/转换输入；decimal 字符串转 `Decimal`，date 转 `date`。
- `registry.py`：`PROTOCOL_VERSION`、`COMMANDS`、`execute_command()`。
- `adapters/`：每个命令的 manifest、handler 和错误映射。

## 新增一个命令

1. 在 `adapters/` 增加模块，导出 `MANIFEST`、`handle()`、`COMMAND`。
2. 在 `adapters/__init__.py` 的 `COMMANDS` 中登记。
3. 在前端 `command-registry.ts` 的 `ENABLED_COMMANDS` 中放行；不放行就不会出现在命令浏览器。
4. 补 `tests/test_command_protocol.py` 的成功与错误用例。
5. 更新协议文档和 `src/INDEX.md`。

只包装稳定、对页面有意义的能力；`clothing_cost`、`annual_mortgage` 这类内部辅助函数不是命令。

## 约定

- 输入严格校验，未知字段直接 422；不要静默忽略拼错的字段。
- `decimal` 输入是字符串，输出也是字符串；`date` 输入是 `YYYY-MM-DD`。
- manifest 的 `question`、`unit`、`semantic`、`as_of` 是契约的一部分，不是注释。
- 领域模块的输入错误由 adapter 转成 `CommandInputError`；未预期异常交给 API 层 500。
- 不把页面文案、布局、固定三情景写进 manifest。
- 输出类型目前是描述性的，handler 要保证返回字段与 manifest 一致。
- 输出默认 `visible=True`；数组下标、回显输入等实现细节标 `visible=False`，页面结果卡片不渲染它们。
- 页面清单（`src/pages/`）只引用这里的输入输出，不复制文案；改问题文案就改 manifest。

## 测试

```bash
cd src
uv run pytest tests/test_command_protocol.py
```
