"""命令行入口：演示表格，以及 --json 模式。"""

import json
import sys

from yishizhuxing.api import calculate
from yishizhuxing.constants import (
    CHILD_EQUIV,
    EXPECTED_CHILDREN,
    LOAN_YEARS,
    PARTNER_BASE,
    STAT_LIVING_SHARE,
)
from yishizhuxing.costs import (
    clothing_cost,
    education_cost,
    food_cost,
    house_buy_year,
    house_type,
    housing_cost,
    to_real,
    transport_cost,
)
from yishizhuxing.profile import LivingProfile


def main_json(arg: str) -> None:
    """--json '<json>'  或  --json 输入.json  或  --json -（读 stdin）"""
    if arg == "-":
        payload = json.load(sys.stdin)
    elif arg.endswith(".json"):
        with open(arg, encoding="utf-8") as fh:
            payload = json.load(fh)
    else:
        payload = json.loads(arg)
    print(json.dumps(calculate(payload), ensure_ascii=False, indent=2))


def main() -> None:
    p = LivingProfile(
        age=22, city="珠海",
        monthly_expense=11_000,
        retire_age=60,
        partner="有伴侣", children="想要",
        housing_plan="买房自住", lifestyle="舒适",
        clothing_freq="一般", clothing_grade="品牌",
        cooking="一半一半", extra_food=True,
        retire_commute="公交地铁", trip_level="偶尔国内",
        visits_home="一年一两次",
    )

    years = p.life_expectancy - p.age
    retire_t = p.retire_age - p.age

    # 本模块只产出支出；切片、折现、减去收入，都由收益模块处理
    c  = to_real(clothing_cost(p, years))
    f  = to_real(food_cost(p, years))
    h  = to_real(housing_cost(p, years))
    tr = to_real(transport_cost(p, years))
    ed = to_real(education_cost(p, years))

    print("=" * 72)
    print("  衣食住行 · 逐年支出（今天的购买力，只含通胀，不含任何收益）")
    print("=" * 72)
    print(f"  你 {p.age} 岁，计划 {p.retire_age} 岁退休（还有 {retire_t} 年），"
          f"测算至 {p.life_expectancy} 岁")
    print(f"  家庭：{p.partner} + {p.children}孩子 → 等效成人 "
          f"{PARTNER_BASE[p.partner] + CHILD_EQUIV * EXPECTED_CHILDREN[p.children]:.2f} 人")
    print(f"  房子：{p.housing_plan}（{house_type(p)}）· 生活档次：{p.lifestyle}")
    print()

    print(f"  {'年龄':>4} {'状态':>4} {'衣':>8} {'食':>9} {'住':>10} "
          f"{'行':>8} {'教育':>10} {'合计':>11}")
    print("  " + "-" * 70)
    for i in range(0, years, 5):
        tot = c[i] + f[i] + h[i] + tr[i] + ed[i]
        flag = "退休" if i >= retire_t else "工作"
        print(f"  {p.age+i:>4} {flag:>4} {c[i]:>8,.0f} {f[i]:>9,.0f} {h[i]:>10,.0f} "
              f"{tr[i]:>8,.0f} {ed[i]:>10,.0f} {tot:>11,.0f}")

    tail = [c[i] + f[i] + h[i] + tr[i] + ed[i] for i in range(retire_t, years)]
    print()
    print(f"  退休那一年支出：{tail[0]:,.0f} 元")
    print(f"  退休后 {len(tail)} 年合计：{sum(tail):,.0f} 元（未扣任何收益）")

    bt = house_buy_year(p)
    edu_years = [i for i, v in enumerate(ed) if v > 0]
    print()
    print("关键节点：")
    if p.housing_plan == "买房自住":
        print(f"  · {p.age + bt} 岁买房：首付 + 持有成本 ≈ {h[bt]:,.0f} 元（一次性）")
        end = bt + LOAN_YEARS
        if end < years:
            print(f"  · {p.age + end} 岁房贷还完，住房支出降至 {h[end]:,.0f} 元/年")
    if edu_years:
        print(f"  · 教育支出：{p.age + edu_years[0]} ~ {p.age + edu_years[-1]} 岁"
              f"（峰值 {max(ed):,.0f} 元/年）")

    # ---- 口径校验 ----
    # 你填的每月支出是「全部消费」（含医疗、娱乐、其他），
    # 而本模块只算衣食住行四项，所以不能直接相减——
    # 换成「你的总支出 × 统计局的四项占比」再比。
    stated = p.monthly_expense * 12
    modeled = c[0] + f[0] + h[0] + tr[0] + ed[0]
    expected = stated * STAT_LIVING_SHARE
    diff = modeled / expected - 1
    print()
    print("口径校验（现在这一刻）：")
    print(f"  · 你填的每月支出 {p.monthly_expense:,.0f} 元 → 年 {stated:,.0f} 元（全部消费）")
    print(f"  · 统计局 2025 城镇口径：衣食住行占消费支出 {STAT_LIVING_SHARE:.1%}")
    print(f"  · 按此比例，其中应有约 {expected:,.0f} 元花在这四项")
    print(f"  · 模型按「{p.lifestyle}档」算出 {modeled:,.0f} 元，偏差 {diff:+.1%}")
    if abs(diff) > 0.20:
        print("  ⚠ 偏差超过 20%：要么档次选错了，要么每月支出填得和实际不符。")
    print()
    print("  注：模型居住只算现金支出，统计局口径含自有住房虚拟租金，")
    print("      所以住这一项天然会低于统计值，属于口径差异，不是漏算。")
    print()


def run(argv: list[str]) -> None:
    """根据命令行参数分派到演示或 --json。"""
    if len(argv) > 1 and argv[1] == "--json":
        main_json(argv[2] if len(argv) > 2 else "-")
    else:
        main()
