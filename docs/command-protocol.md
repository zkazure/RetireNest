# 命令协议 v1

RetireNest 后端把领域能力暴露为**命令**：一个命令回答一个明确的问题，接收一组输入，返回领域输出。前端不通过页面级聚合接口取数据，而是从命令清单里选择命令，在页面代码里自由组合。

本期协议版本：`1.0.0`。当前注册四个命令：

- `medical.estimate`
- `pension.basic`
- `deposit.demand`
- `living.calculate`

现有退休规划页和 `POST /api/retirement/plan` 保持不变；命令协议是并行的新接口。

## 1. 端点

```
GET  /api/commands
POST /api/commands/{command_id}
```

- `GET /api/commands`：返回协议版本和全部命令 manifest。
- `POST /api/commands/{command_id}`：执行一个命令。
- 没有鉴权头、Cookie 或 API Key。
- 请求和响应都是 `application/json`。

## 2. 命令清单

```json
{
  "protocol_version": "1.0.0",
  "commands": [
    {
      "id": "medical.estimate",
      "version": "1.0.0",
      "question": "在当前年龄、城市和医保类型下，医疗预算大概多少？",
      "description": "按 2025 年参考价格估算年度和月度医疗消费；调整系数为演示假设。",
      "deterministic": true,
      "as_of": "2025",
      "inputs": [],
      "outputs": [],
      "examples": []
    }
  ]
}
```

`protocol_version` 是清单协议版本；每个命令的 `version` 独立演进。

## 3. Manifest

### 命令级字段

- `id`：稳定标识，使用 `domain.action` 小写形式。
- `version`：命令版本；执行请求必须回传相同版本。
- `question`：命令回答的问题，给前端开发者和文档使用，不是 LLM prompt。
- `description`：补充说明。
- `deterministic`：相同输入、相同版本、相同 `as_of` 是否得到相同输出。
- `as_of`：数据基准时间，例如医疗的 2025 价格年、利率快照的抓取日期。
- `inputs`：输入规格数组。
- `outputs`：输出规格数组。
- `examples`：示例输入，便于文档和调试。

### 输入规格

```json
{
  "name": "age",
  "question": "你现在多少岁？",
  "type": "integer",
  "unit": "岁",
  "required": true,
  "default": null,
  "options": [],
  "constraints": { "min": 0, "max": 120 },
  "semantic": "age",
  "required_when": null
}
```

支持的输入 `type`：

- `integer`：JSON 整数，拒绝布尔值和浮点。
- `number`：有限 JSON 数字。
- `decimal`：JSON **字符串**，例如 `"100000.20"`；不接受科学计数法。
- `date`：`YYYY-MM-DD`。
- `enum`：字符串，必须在 `options` 中。
- `boolean`：`true` / `false`。
- `text`：字符串，提交前去掉首尾空格。

`constraints` 支持：

- `min`、`max`：数值/decimal 范围。
- `precision`：decimal 最多小数位。
- `max_length`：text 最大字符数。

`required_when` 用于条件必填：

```json
{ "field": "gender", "equals": "女" }
```

`default` 只在输入缺失时使用；有默认值的可选输入可以省略。

### 输出规格

```json
{
  "name": "total",
  "question": "合计月养老金",
  "type": "decimal",
  "unit": "元/月",
  "semantic": "money_per_month_nominal",
  "precision": 2,
  "time_axis": null
}
```

输出 `type` 目前是描述性的：

- `integer`、`number`、`decimal`、`text`
- `series`：数组
- `object`：嵌套对象

`decimal` 输出是字符串，避免精度丢失。`time_axis` 描述序列的时间轴，例如：

```json
{ "start": "age", "step_years": 1, "length_field": "years" }
```

### 语义类型

`semantic` 帮助前端开发者判断输出能否接到输入，当前约定：

- `age`、`date`、`duration_years`
- `money_per_month_nominal`、`money_per_month_real`
- `money_per_year_nominal`、`money_per_year_real`
- `money_total_nominal`、`money_total_real`
- `ratio`（0.02 表示 2%）、`percent`（2 表示 2%）
- `yearly_series<money_per_year_nominal>` 等

单位不同、名义/实际不同、序列与标量不同，都不能直接连线；需要显式 adapter。

## 4. 执行

请求：

```json
{
  "version": "1.0.0",
  "inputs": {
    "age": 30,
    "city": "广州",
    "insurance": "职工医保"
  }
}
```

成功响应：

```json
{
  "command_id": "medical.estimate",
  "version": "1.0.0",
  "outputs": {
    "age_group": "18–39岁",
    "annual_medical_cost": 1976.06,
    "monthly_medical_cost": 164.67,
    "note": "演示估算，调整系数尚未校准；按2025年参考价格，不代表个人实际医疗费。"
  },
  "meta": {
    "deterministic": true,
    "as_of": "2025"
  }
}
```

输入规则：

- 未知输入字段直接 422，不静默忽略。
- 缺必填字段、类型错误、枚举错误、范围错误返回 422。
- 条件必填由 `required_when` 校验。
- 领域模块抛出的输入错误会被适配器转成 422；未预期异常返回 500。

## 5. 错误

```json
{
  "code": "INVALID_INPUT",
  "message": "请检查输入。",
  "field_errors": [
    { "field": "age", "message": "请填写。" }
  ]
}
```

状态码与 code：

- 404 `UNKNOWN_COMMAND`：命令不存在。
- 409 `UNSUPPORTED_VERSION`：`version` 与 manifest 不一致。
- 422 `INVALID_INPUT`：输入校验失败，带 `field_errors`。
- 500 `COMMAND_FAILED`：命令执行失败，不返回堆栈。

请求体本身格式错误（非法 JSON、顶层多字段）仍走 FastAPI 的 422 `VALIDATION_ERROR`，与命令输入错误区分。

## 6. 版本与确定性

- `protocol_version` 是清单协议版本；破坏性变更升主版本。
- 每个命令独立 `version`；执行请求必须回传当前版本。
- 新增可选输出可以保持版本；删除/改名/改单位必须升版本。
- 响应回显 `command_id`、`version`、`meta.deterministic`、`meta.as_of`。
- 命令不得依赖隐藏的“今天”；需要日期基准时写进 `as_of` 或输入。

## 7. 前端注册表

命令清单是后端能力表；前端另有显式注册表 `frontend/src/command-registry.ts`：

```ts
const ENABLED_COMMANDS = new Set([
  'medical.estimate',
  'pension.basic',
  'deposit.demand',
  'living.calculate',
]);
```

启动时读取 `GET /api/commands`，只注册允许列表内的命令。后端新增命令不会自动出现在页面里，前端开发者要显式放行。

页面通过：

```ts
const response = await runCommand('medical.estimate', {
  age: 30,
  city: '广州',
  insurance: '职工医保',
});
```

获取输出。页面如何排版、调用哪些命令、把哪个输出接到哪个输入，由前端代码决定；后端不返回页面结构。

命令浏览器 `frontend/commands.html` 是开发者工具：左侧命令列表，右侧按 manifest 自动生成输入表单，执行后展示 JSON 输出。它不做页面级组合。

## 8. 现有命令

### medical.estimate

- 问题：当前年龄、城市、医保类型下医疗预算多少。
- 输入：`age`、`city`、`insurance`。
- 输出：`age_group`、`annual_medical_cost`、`monthly_medical_cost`、`note`。
- `as_of`：`2025`。

### pension.basic

- 问题：退休当月能领多少城镇职工基本养老金。
- 输入：`birth_date`、`gender`、`category`（女性必填）、`contribution_years`、`average_index`、`account_balance`、`calculation_base`，可选 `prior_monthly_wage`、`annual_adjustment`。
- 输出：`retirement_age_months`、`payout_months`、`basic_pension`、`account_pension`、`total`、`annual_adjustment`、`replacement_rate`、`calculation_base`、`average_index`、`contribution_years`。
- `as_of`：`2025`。

### deposit.demand

- 问题：一笔活期存款到期能拿多少利息。
- 输入：`principal`、`start_date`、`end_date`，可选 `annual_rate`。
- 输出：`principal`、`annual_rate`、`days`、`interest`、`total`。
- `as_of`：利率快照的抓取日期。

### living.calculate

- 问题：退休前后每年衣食住行要花多少钱。
- 输入：`LivingProfile` 的 18 个字段；城市为当前 44 城枚举。
- 输出：`years`、`retire_index`、`inflation`、`edu_inflation`、`nominal`、`real`。
- `nominal`/`real` 是对象，内含 `clothing`、`food`、`housing`、`transport`、`education`、`total` 数组；时间轴从 `age` 起，步长 1 年。

## 9. 与旧接口的关系

- `POST /api/retirement/plan` 继续服务现有退休规划页，返回页面级 `PlanResponse`。
- 新命令协议不依赖旧接口；旧接口也不调用新命令。
- 迁移策略：新页面使用命令注册表；现有页面保持不动，等有明确需求再拆成命令组合。
- 不在本期提供 `plan.projection`、三情景命令或页面级组合器。

## 10. 非目标

- 不做终端用户拖拽连线。
- 不做 LLM 自动选命令。
- 不做命令批量执行或依赖 DAG。
- 不做动态枚举选项服务；选项当前写在 manifest。
- 不做鉴权、多用户、持久化。
- 输出类型目前不强制校验；适配器负责返回与 manifest 一致的字段。
