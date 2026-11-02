"""三项输入的医疗支出参考原型。调整系数均为演示假设，不是统计估计。"""

from math import isfinite

# 官方参考：2025 年全国居民人均医疗保健消费支出。
# https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962321.html
# 这不是年龄别临床医疗费或医保报销前总费用，不能再扣一次报销比例。
BASE_ANNUAL_COST = 2573.0
PRICE_YEAR = 2025

# 下列全部为产品演示参数，未经过统计校准；可以集中替换。
# 年龄因素、地区因素、医保因素为相对全国消费参考值的调整，非报销比例。
AGE_FACTORS = (
    (0, 17, "0–17岁", 0.6),
    (18, 39, "18–39岁", 0.8),
    (40, 59, "40–59岁", 1.1),
    (60, 74, "60–74岁", 1.8),
    (75, 120, "75岁及以上", 2.5),
)
CITY_FACTORS = {"北京": 1.2, "上海": 1.2, "广州": 1.2, "深圳": 1.2}
INSURANCE_FACTORS = {"职工医保": 0.8, "居民医保": 1.0, "无医保": 1.5}
INSURANCE_ALIASES = {
    "职工基本医疗保险": "职工医保",
    "城镇职工医保": "职工医保",
    "城乡居民医保": "居民医保",
    "城乡居民基本医疗保险": "居民医保",
    "未参保": "无医保",
}


def estimate_medical_cost(age: int, city: str, insurance: str) -> dict:
    """只需年龄、居住城市、医保类型，返回当前年龄段的年度/月均费用参考。

    结果使用 2025 年参考价格，属于含演示系数的粗略消费预算。
    不预测退休年龄或未来价格，不包含单独计算的保费和长期护理费。
    三项信息对应同一年龄段时使用相同参数，不输出逐年表或退休资金需求。
    """
    if isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 120:
        raise ValueError("年龄必须是 0 至 120 之间的整数")
    if not isinstance(city, str) or not city.strip():
        raise ValueError("请提供居住城市，例如：上海")
    if not isinstance(insurance, str):
        # 所有无效输入统一使用已公开的 ValueError 接口。
        raise ValueError("医保类型请选择：职工医保、居民医保、无医保")  # noqa: TRY004
    city = city.strip().removesuffix("市")
    if not city:
        raise ValueError("请提供有效的城市名称")
    insurance = insurance.strip()
    insurance = INSURANCE_ALIASES.get(insurance, insurance)
    if insurance not in INSURANCE_FACTORS:
        raise ValueError("医保类型请选择：职工医保、居民医保、无医保")
    for start, end, label, age_factor in AGE_FACTORS:
        if start <= age <= end:
            break
    city_factor = CITY_FACTORS.get(city, 1.0)
    estimate = BASE_ANNUAL_COST * age_factor * city_factor * INSURANCE_FACTORS[insurance]
    if not isfinite(estimate) or estimate < 0:
        raise ValueError("模型参数必须产生非负有限金额")
    annual = round(estimate, 2)
    note = "演示估算，调整系数尚未校准；按2025年参考价格，不代表个人实际医疗费。"
    if city not in CITY_FACTORS:
        note += "该城市暂用全国地区系数。"
    return {
        "age_group": label,
        "annual_medical_cost": annual,
        "monthly_medical_cost": round(annual / 12, 2),
        "note": note,
    }
