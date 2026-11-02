# 命令协议 v1.1

RetireNest 后端把领域能力暴露为**命令**：一个命令回答一个明确的问题，接收一组输入，返回领域输出。前端不通过页面级聚合接口取数据，而是从命令清单里选择命令，在页面代码里自由组合。

本期协议版本：`1.1.0`。当前注册十一个命令：

- `plan.retirement`
- `medical.estimate`
- `pension.basic`
- `deposit.demand`
- `living.calculate`
- `savings.project`
- `savings.goal`
- `inflation.convert`
- `simulation.retirement`
- `withdrawal.safe_rate`
- `longevity.estimate`

后六个是退休规划的计算原语：储蓄增长、目标倒推、通胀换算、蒙特卡洛、安全提取率与寿命估计。它们不进入主页表单，供命令浏览器、开发者和后续 Agent 直接调用；主页仍使用前五个命令。

退休规划主页由页面清单驱动：`GET /api/pages/retirement` 告诉前端有哪些字段、怎么分组、提交时调用哪些命令；前端逐个执行命令并组合结果。`POST /api/retirement/plan` 保留为过渡接口。

## 1. 端点

```
GET  /api/commands
POST /api/commands/{command_id}
GET  /api/pages/{page_id}
```

- `GET /api/commands`：返回协议版本和全部命令 manifest。
- `POST /api/commands/{command_id}`：执行一个命令。
- `GET /api/pages/{page_id}`：返回页面清单，见第 5 节。
- 没有鉴权头、Cookie 或 API Key。
- 请求和响应都是 `application/json`。

## 2. 命令清单

```json
{
  "protocol_version": "1.1.0",
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
      "examples": [],
      "when_to_use": "用户问医疗预算时用。",
      "when_not_to_use": "用户问退休资金缺口时用 plan.retirement。"
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
- `deterministic`：相同输入、相同版本、相同 `as_of` 是否得到相同输出。固定 seed 的蒙特卡洛也算确定：它可复现，但不代表没有随机性。
- `as_of`：数据基准时间，例如医疗的 2025 价格年、利率快照的抓取日期、寿命参数的 2020 基准。
- `inputs`：输入规格数组。
- `outputs`：输出规格数组。
- `examples`：示例输入，便于文档和调试。
- `when_to_use`：什么时候该选这个工具；可选的工具选择指引，页面不展示。
- `when_not_to_use`：什么时候该换另一个工具；与 `when_to_use` 一起防止模型误用相近工具。

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
  "required_when": null,
  "description": "周岁，整数；结果条件于已经活到这个年龄。"
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

`description` 是给工具调用方（尤其是 LLM）看的参数说明，写清单位、名义/实际口径、与其它参数的关系。它不替代 `question`：`question` 是页面文案，`description` 是工具语义。

### 输出规格

```json
{
  "name": "total",
  "question": "合计月养老金",
  "type": "decimal",
  "unit": "元/月",
  "semantic": "money_per_month_nominal",
  "precision": 2,
  "time_axis": null,
  "visible": true,
  "description": "基础养老金加个人账户养老金，按退休时点。"
}
```

`visible` 为 `false` 表示这是实现细节（数组下标、回显输入、结构化结果），页面不展示；模块结果卡片只渲染 `visible` 的输出。

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

## 5. 页面清单

`GET /api/pages/{page_id}` 只描述页面结构，不返回测算结果：

- `sections`：分组、顺序与可选开关；每个字段带 `label`、类型、单位、选项、约束、`required`、`visibleWhen`。
- `executions`：提交时按顺序执行的命令。`inputs` 把命令参数映射到页面字段；`toggle` 非空时只有开关打开才执行；`outputs` 是结果展示所需的输出规格。
- `rules`：跨字段预校验，前端只做即时提示，命令校验仍是权威。

字段的 `label` 必须等于来源命令 manifest 的 `question`。同一字段被多个命令消费时，`min`/`max`/`precision`/`max_length` 取交集，且每次请求现算，前端不持有数值常量。

字段的 `required` 由页面清单声明：默认必答，`false` 表示可留空。页面标 `false` 的字段，其所有消费命令的对应输入也必须可选，否则解析失败。命令的 `required_when` 只作用于命令输入，不在页面上推导；条件必填用 `visibleWhen`，字段只在条件成立时出现，出现即必答。

```json
{
  "id": "retirement",
  "version": "1.0.0",
  "sections": [
    {
      "id": "basic",
      "title": "基本情况",
      "fields": [
        {
          "name": "age",
          "label": "你现在多少岁？",
          "type": "number",
          "integer": true,
          "required": true,
          "unit": "岁",
          "min": 18,
          "max": 80,
          "source": { "command": "plan.retirement", "input": "age" }
        }
      ]
    }
  ],
  "executions": [
    {
      "command": "plan.retirement",
      "version": "1.0.0",
      "question": "按现在的收入和支出，退休时能攒下多少、还差多少？",
      "inputs": { "age": "age" },
      "toggle": null,
      "outputs": []
    }
  ],
  "rules": []
}
```

页面清单不包含测算逻辑，也不决定结果怎么排版；结果由各命令的输出组成。

## 6. 错误

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

## 7. 版本与确定性

- `protocol_version` 是清单协议版本；破坏性变更升主版本。1.1 新增 `InputSpec.description`、`OutputSpec.description`、`CommandManifest.when_to_use` / `when_not_to_use`，都是可选字段，命令版本保持 1.0.0。
- 每个命令独立 `version`；执行请求必须回传当前版本。
- 新增可选输出可以保持版本；删除/改名/改单位必须升版本。
- 响应回显 `command_id`、`version`、`meta.deterministic`、`meta.as_of`。
- 命令不得依赖隐藏的“今天”；需要日期基准时写进 `as_of` 或输入。
- 固定 `seed` 的蒙特卡洛仍标 `deterministic: true`：相同输入得到相同输出；它不等于“结果没有随机性”。

## 8. 前端注册表

命令清单是后端能力表；前端另有显式注册表 `frontend/src/command-registry.ts`：

```ts
const ENABLED_COMMANDS = new Set([
  'plan.retirement',
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

命令浏览器 `frontend/commands.html` 是开发者工具：左侧命令列表，右侧按 manifest 自动生成输入表单。表单下的“填充示例”写入 `examples[0].inputs`，“清空”回到 manifest 的 `default`。执行后先按 `outputs` 渲染输出表（只列 `visible !== false`，`decimal` 原样、数组与对象只做摘要），完整响应折叠在“原始 JSON”里。必填与 `required_when` 会同步到原生校验，校验不过不发请求；后端 422 仍按字段展示。它不做页面级组合。

## 9. 现有命令

### plan.retirement

- 问题：按现在的收入和支出，退休时能攒下多少、还差多少。
- 输入：`city`、`age`、`retire_age`、`life_expectancy`、`monthly_income`、`monthly_expense`、`assets`、`retirement_expense`、`nominal_return`、`inflation`；`debt`、`monthly_pension` 可省略，按 0 计。
- 输出：`target`、`projected`、`gap`、`coverage`、`required_monthly_saving`、`monthly_surplus`，以及 `points`、`scenarios`、`explanation`、`warnings`、`plan_input`。
- `points`、`scenarios`、`plan_input` 等结构字段标 `visible: false`，只供页面组合使用。

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

以下六个是 1.1 新增的计算原语，默认口径与 `plan.retirement` 一致：实际购买力、按年、年末投入。

### savings.project

- 问题：给定当前储蓄、每月投入、名义回报率、通胀率和年限，未来能攒到多少。
- 输入：`current_savings`、`monthly_contribution`、`annual_return_pct`、`inflation_pct`、`years`；可选 `compounding`（按年/按月，默认按年）、`timing`（期末/期初，默认期末）。
- 输出：`future_balance_real`、`future_balance_nominal`、`total_contributions_real`、`total_invested_real`、`growth_real`、`real_return_pct`、`assumptions`。
- 月投入按实际值恒定；`total_invested_real` 含当前储蓄，`total_contributions_real` 只算新增投入。

### savings.goal

- 问题：想达到一个目标金额，每月需要存多少。
- 输入：`target_amount`、`current_savings`、`annual_return_pct`、`inflation_pct`、`years`，可选 `compounding`、`timing`。
- 输出：`required_monthly_contribution_real`、`required_annual_contribution_real`、`projected_without_contribution_real`、`shortfall_real`、`real_return_pct`、`assumptions`。
- 目标已被现有储蓄覆盖时，投入要求为 0；不要用 `savings.project` 反复试参数。

### inflation.convert

- 问题：一笔名义金额相当于今天多少购买力，或反过来。
- 输入：`amount`、`annual_inflation_pct`、`years`、`direction`（名义转实际/实际转名义，默认名义转实际）。
- 输出：`converted_amount`、`cumulative_factor`、`annual_inflation_pct`、`direction`、`note`。
- `savings.*` 与 `simulation.*` 已内含通胀，不要再用本命令折算它们的输出。

### simulation.retirement

- 问题：按当前储蓄和投入，退休后钱会不会用完。
- 输入：`current_savings`、`monthly_contribution`、`years_to_retirement`、`retirement_years`、`annual_retirement_expense`、`annual_return_pct`、`volatility_pct`、`inflation_pct`；可选 `monthly_pension`（默认 0）、`paths`（默认 2000）、`seed`（默认 42）。
- 输出：`success_rate`、`failed_paths`、`median_terminal_balance_real`、`p10_terminal_balance_real`、`p90_terminal_balance_real`、`median_depletion_year`，以及结构字段 `terminal_balance_percentiles`、`depletion_year_percentiles`、`balance_percentiles`、`paths`、`seed`、`assumptions`、`note`。
- 模型：名义毛收益率对数正态，通胀确定性折算；每年年末投入或支取。余额为负即视为耗尽。
- 成功定义：退休期内任何一年年末余额都不为负。`success_rate` 是路径占比，不是概率保证；固定 `seed` 使结果可复现。

### withdrawal.safe_rate

- 问题：退休时有一笔钱，每年可以安全提取多少。
- 输入：`retirement_savings`、`retirement_years`、`annual_return_pct`、`volatility_pct`、`inflation_pct`；可选 `target_success_rate`（默认 90）、`paths`、`seed`。
- 输出：`safe_withdrawal_rate_pct`、`annual_withdrawal_real`、`monthly_withdrawal_real`、`success_rate_at_rate`、`depletion_year_percentiles`、`paths`、`seed`、`assumptions`、`note`。
- 在同一组路径上对提取比例二分，找满足目标成功率的最高比例；提取额按实际购买力固定。

### longevity.estimate

- 问题：按年龄、性别和健康状况，大概能活到多少岁。
- 输入：`current_age`、`sex`（男/女）、`health`（较差/一般/良好，默认一般）。
- 输出：`median_age_at_death`、`p10/p25/p75/p90_age_at_death`、`probability_to_85`、`probability_to_90`、`probability_to_95`、`median_remaining_years`、`life_expectancy_at_birth_used`、`assumptions`。
- `as_of`：`2020`。基准寿命、Gompertz 离散参数和健康档位平移都是演示假设，不是生命表或医学预测；概率用百分数（21.4 表示 21.4%）。

## 10. 与旧接口的关系

- `POST /api/retirement/plan` 保留为过渡接口，仍返回页面级 `PlanResponse`；新前端不再调用。
- `plan.retirement` 与旧接口共用 `plan/payload.py` 的构造器，结果字段结构一致。
- 主页通过页面清单逐个调用命令；医疗、养老、存款、生活支出的结果单独展示，不并入退休资金目标。
- 不在本期提供 `plan.projection`、命令 DAG 或后端页面组合器。

## 11. 非目标

- 不做终端用户拖拽连线。
- 命令层不调用 LLM；协议 1.1 的 `description`、`when_to_use`、`when_not_to_use` 是给后续 Agent 层生成工具 schema 用的，Agent 尚未接入。
- 不做税务工具；`pension.basic` 只覆盖社保养老金，税制是地区规则，等有明确地区后再加。
- 后端不做批量执行或依赖 DAG；页面的顺序执行由前端按页面清单完成。
- 不做动态枚举选项服务；选项写在 manifest，页面清单原样引用。
- 不做服务端页面组合器：页面清单只描述结构与执行顺序，不返回结果。
- 不做鉴权、多用户、持久化。
- 输出类型目前不强制校验；适配器负责返回与 manifest 一致的字段。
