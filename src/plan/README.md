# plan：退休规划共用的数据结构

计算已经拆到专门模块：全周期现金流在 `lifecycle`，养老金在 `pension`，医疗在 `medical`，
生活支出在 `living`，存款在 `deposit`。这里只保留命令校验、页面解析与 API 错误映射共用的
`FieldError`，以及历史遗留的规划输入输出结构。

## 口径

`FieldError(field, message)` 是跨层共用的字段错误：命令校验、页面解析与 HTTP 错误响应都
用它把错误定位到具体字段，前端据此高亮。

新增计算逻辑请放到对应的领域模块，不要再往这里加。
