# 动态表单模板与后端对接约定

这是前端先行定义的协议，不代表当前 Python 仓库已经实现 HTTP 接口。

## 先看哪些文件

- `src/form-template.json`：唯一的业务字段配置。字段名、类型、分组、默认值、选项、显示条件与跨字段规则在这里维护。
- `src/form-types.ts`：模板、字段、请求、字段错误的 TypeScript 类型。
- `src/form-renderer.ts`：通用渲染和错误定位，不写具体业务字段名。
- `src/form-data.ts`：模板检查、条件过滤、类型转换与请求构造。
- `src/form-adapter.ts`：暂时把基础字段映射到原本的本地演示引擎。
- `src/plan-contract.ts`：建议的规划成功/失败响应类型。
- `contracts/plan-request.example.json`：默认表单的实际请求示例。
- `contracts/plan-request-all-modules.example.json`：所有可选模块开启的实际请求示例。
- `contracts/plan-response.example.json`：基于默认值计算的完整响应示例。
- `contracts/plan-error.example.json`：字段错误响应示例。

## 字段怎么增加

在合适的 `sections[].fields` 里增加一项即可，例如：

```json
{
  "name": "desired_hobby",
  "label": "退休后想培养的爱好",
  "type": "text",
  "maxLength": 100,
  "placeholder": "例如园艺、摄影"
}
```

界面自动出现输入框；填写后自动进入 `values.desired_hobby`。不需要改 main.ts、渲染器或请求字段白名单。前端模板与后端处理规则一并升级版本。

支持的控件：`text`、`number`、`decimal`、`date`、`select`、`checkbox`、`textarea`。增加全新控件类型仍需扩展渲染器和校验逻辑；增加同类型字段只改 JSON。新增字段不自动参与本地演示计算，也不会自动增加图表或 PDF 结果项。

字段 name 必须唯一，使用小写 snake_case；只允许字母开头和字母、数字、下划线。模板作为纯数据处理，不支持 HTML、JS 表达式或动态脚本。

## 模板结构

顶层：`id`、`version`、`title`、`description`、`optionSets`、`sections`、`rules`。

分组：`id`、`title`、`fields`，可选 `description`、`collapsible`、`toggle`。`collapsible: true` 只折叠视觉显示，字段仍提交；`toggle` 关闭会禁用并排除整组业务字段。

```json
{
  "id": "medical",
  "title": "医疗预算信息",
  "toggle": {
    "name": "medical_enabled",
    "label": "填写医保信息",
    "defaultValue": false
  },
  "fields": [
    {
      "name": "insurance",
      "label": "医保类型",
      "type": "select",
      "required": true,
      "options": [
        { "label": "职工医保", "value": "职工医保" },
        { "label": "居民医保", "value": "居民医保" },
        { "label": "无医保", "value": "无医保" }
      ],
      "defaultValue": "职工医保"
    }
  ]
}
```

通用字段属性：`required`、`defaultValue`、`placeholder`、`hint`、`maxLength`、`unit`。number 还可配置 `integer`、`min`、`max`、`step`；decimal 支持 `precision`、`min`、`max`。

select 的 `options` 和 `optionsSource` 二选一。后者引用顶层 `optionSets`；每项固定为 `{label, value}`。`allowCustom: true` 时自动提供“其他（自行填写）”，提交实际输入的文字，不提交“其他”或特殊占位值。

条件显示示例：

```json
"visibleWhen": [{ "field": "gender", "equals": "女" }]
```

多个条件按“全部满足”处理。引用的控制字段自身也必须可见。暂不提供复杂表达式。checkbox 的 equals 用布尔值，其他控件用原始字符串值；数字控件条件也用字符串。循环条件或未知字段引用会被模板校验拒绝。

跨字段规则支持 `lessThan`、`dateBefore`、`minimumDifference`，失败时定位到 right 字段。当前已配置年龄顺序、父母子女年龄差和存款日期顺序。

## 请求格式

建议后续实现 `POST /api/retirement/plan`，Content-Type 为 application/json。路径是本协议建议，当前未发网络请求。

```json
{
  "template_id": "retirenest-retirement",
  "schema_version": "1.0.0",
  "values": {
    "age": 28,
    "city": "广州",
    "retire_age": 55,
    "medical_enabled": false,
    "pension_enabled": false,
    "deposit_enabled": false
  }
}
```

上面是结构节选；完整数据以 contracts 中的文件为准。页面提交时先验证，再调用 `buildRequest(template, values)` 构造这个对象。

序列化规则：

- number 提交 JSON number；`integer: true` 要求安全整数。
- decimal 提交 JSON string，保留输入精度，例如 `"100000.20"`；不接受科学计数法。后端转换为 Decimal，不能先转 float。
- checkbox 提交真正的 true/false，不是字符串。
- date 提交 `YYYY-MM-DD` 字符串；后端转为 date。
- text、select、textarea 去掉首尾空格后提交 string；选项提交 value。
- 可见且非必填的空值提交 null；后端调用有缺省值的 Python 函数前，应省略这些 null 项，让函数使用默认值。
- 关闭模块、条件隐藏字段从 values 中省略，之前输入的内容保留在页面以便切回，但不会提交。
- 模块开关本身始终提交。折叠与关闭模块不同：折叠字段仍然提交和校验。
- API Key 是独立输入，不在模板、业务 payload、请求示例或 PDF 中。

金额默认单位为元；带 unit 的字段以该单位解释。`nominal_return` 和 `inflation` 用百分数（3 表示 3%）；`annual_rate` 和 `annual_adjustment` 用十进制比例字符串（"0.02" 表示 2%），界面有明确提示。

## 后端怎么接

后端负责校验 template_id/schema_version、类型、枚举、范围和跨字段关系，再按模块分发。不要把整个 values 原样传给目前的每个 Python 函数：生活支出模块会拒绝未知字段。

- 生活支出：取 age、city、monthly_expense、retire_age、life_expectancy 以及 living 分组字段。
- 医疗：medical_enabled 为 true 时取 age、city、insurance。
- 养老金：pension_enabled 为 true 时取 pension 分组字段；把日期转 date，decimal 字符串转 Decimal。女性时 category 必填。
- 存款：deposit_enabled 为 true 时取 principal、annual_rate、start_date、end_date，转换 Decimal 与 date。
- 前端 city 允许自定义城市，后端需补充城市处理策略，不能直接沿用生活模块的严格 44 城限制而无提示。
- 自填 age 与出生日期的口径由后端统一校验；期望退休年龄与养老金模块的法定退休年龄不能直接混用。
- 支出、医疗和养老金不同模块的计价年份、通胀口径及时间序列起点，需在综合规划层统一，避免重复计入支出。

如果后续由后端提供表单配置，建议 `GET /api/retirement/form-schema` 返回与 form-template.json 相同的结构；前端把本地 JSON 来源替换成请求结果，仍使用同一个 validateTemplate 和 FormRenderer。当前尚未实现远程加载或计算 HTTP 请求。

## 响应格式

成功响应建议返回 plan-contract.ts 定义的 PlanResponse：template_id、schema_version、mode、plan_input、result、scenarios、explanation、warnings。完整示例在 contracts/plan-response.example.json。

- plan_input 沿用现有 PlanInput 的 camelCase 字段，只表示用于结果摘要和 PDF 的标准化基础假设，不包含扩展原始信息。
- result 使用现有 PlanResult：target/projected/gap 单位元，coverage 为百分数，realReturn 为小数比例，points 按年龄递增，depletedAge 无资金不足时为 null。
- scenarios 返回三种情景的目标、预计资产和缺口；真实结果接入后，前端应直接显示后端返回结果，不能继续用本地公式重算。
- explanation 与 warnings 是纯文本，前端展示时不当作 HTML。
- 输入错误建议 HTTP 422，返回 code/message/field_errors，field 使用 values 中的同名字段。版本不匹配建议 HTTP 409；未知版本不应悄悄按另一个版本计算。

当前页面依旧使用 form-adapter.ts 和 model.ts 的基础字段进行本地演示；扩展信息已完整收集，但没有接入 Python 或 AI。结果页明确提示这一点。现有 PDF 同样导出基础演示结果。后端接入时再将本地计算与结果渲染入口替换为真实响应。

## 验证

```powershell
npm test
npm run build
```

测试包含：新增模板字段自动进入请求、模块开关与条件字段、日期与年龄跨字段校验、十进制精度、自定义城市、API Key 排除、无效配置及循环条件。
