# Yishizhuxing

衣食住行：退休前后逐年测算穿衣、饮食、住房、交通、子女教育五项支出。只管花钱，不管收入和投资收益，医疗预算见 `medical/`。

名义值含通胀，实际值按 `to_real` 折回今天的购买力。参数的出处、推导和口径差异写在 `constants.py` 与 `costs.py` 的模块注释里。

## 使用方法

```python
from yishizhuxing import calculate

result = calculate({
    "age": 30,
    "city": "珠海",
    "monthly_expense": 9000,
    "housing_plan": "买房自住",
    "children": "想要",
})

result["years"]        # 55，测算到 85 岁
result["retire_index"] # 30，60 岁退休对应数组下标
result["real"]["total"][0]  # 第一年的总支出，今天的购买力
```

命令行看一份演示：

```
uv run python -m yishizhuxing
uv run python -m yishizhuxing --json '{"age":30,"city":"珠海","monthly_expense":9000}'
```

`--json` 后面可以跟 JSON 字符串、`.json` 文件路径，或者 `-` 从标准输入读。

## 参数

必填三项：`age`（18 岁以上）、`city`（支持 44 个城市）、`monthly_expense`（当前每月总支出，元）。

可选项都有缺省值，前端不传也能算：`child_age_now`、`retire_age`、`life_expectancy`、`partner`、`children`、`housing_plan`、`lifestyle`、`retire_city`、`clothing_freq`、`clothing_grade`、`cooking`、`extra_food`、`retire_commute`、`trip_level`、`visits_home`。枚举字段的合法取值见 `profile.py` 的注释，必须逐字匹配。

## 返回

一个 dict：`years` 是年数，`retire_index` 是退休那一年的下标，`inflation` 和 `edu_inflation` 是所用的通胀率；`nominal` 和 `real` 各含 `clothing`、`food`、`housing`、`transport`、`education`、`total` 六个等长数组，下标 `i` 表示第 `i+1` 年。

## 出错

参数不合法时抛 `LivingCostError`（`ValueError` 的子类），消息写明是哪个字段、期望什么。字段名拼错也会在入口报出来，不会被静默忽略。

## 测试

在 `src/` 下执行：

```
uv run pytest tests/test_yishizhuxing.py
```
