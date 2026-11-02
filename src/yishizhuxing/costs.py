"""每年的「衣、食、住、行、教育」支出。

统一约定：所有函数返回 list[float]，第 i 个元素是「第 i+1 年」的支出，
金额为名义值（已含通胀）。
"""

from yishizhuxing.constants import (
    CHILD_BIRTH_AGE,
    CHILD_EQUIV,
    CHILD_MARGINAL,
    CITY_COEF,
    CITY_TIER,
    CLOTHING_BASE,
    CLOTHING_FREQ,
    CLOTHING_GRADE,
    COMMUTE_BASE,
    COOKING_COEF,
    DOWN_PAYMENT,
    EDU_INFLATION,
    EDU_RATE,
    EXPECTED_CHILDREN,
    EXTRA_FOOD,
    FOOD_BASE,
    HOLDING_COST,
    HOUSE_PRICE,
    INFLATION,
    LIFESTYLE_EDU,
    LOAN_RATE,
    LOAN_YEARS,
    PARTNER_BASE,
    RENT_BASE,
    RENT_GROWTH,
    RENTER_UTILITY,
    TRIP_ANNUAL,
    VISIT_HOME_ANNUAL,
)
from yishizhuxing.profile import LivingProfile

# ============================================================
# 辅助函数
# ============================================================

def city_tier(city: str) -> str:
    return CITY_TIER.get(city, "二线")


def ret_tier(p: LivingProfile) -> str:
    return city_tier(p.retire_city or p.city)


def child_birth_user_age(p: LivingProfile) -> int:
    """用户生第一个孩子时的年龄。

    - 已经有孩子（child_age_now 不为空）：用「现在年龄 − 孩子年龄」反推，
      这样教育窗口能对上真实的孩子年龄，而不是当作现在才生
    - 还没有孩子：按统计初育年龄 30，年龄已经超过的按现在算
    """
    if p.child_age_now is not None:
        return p.age - p.child_age_now
    return max(p.age, CHILD_BIRTH_AGE)


def child_age_at(p: LivingProfile, t: int) -> int:
    return (p.age + t) - child_birth_user_age(p)


def adults_at(p: LivingProfile, t: int) -> float:
    """第 t 年的等效成人数。孩子 18 岁后离家上大学，交给教育类目。"""
    n = PARTNER_BASE[p.partner]
    ca = child_age_at(p, t)
    if 0 <= ca < 18:
        n += CHILD_EQUIV * EXPECTED_CHILDREN[p.children]
    return n


def house_type(p: LivingProfile) -> str:
    """有孩子住两居，否则一居。"""
    return "2bed" if EXPECTED_CHILDREN[p.children] >= 0.5 else "1bed"


def inflation_factor(t: int) -> float:
    return (1 + INFLATION) ** t


def to_real(values: list[float]) -> list[float]:
    """名义金额 → 今天的购买力。对外展示一律用现值，否则 40 年后会膨胀到无法阅读。"""
    return [v / inflation_factor(t) for t, v in enumerate(values)]


def house_buy_year(p: LivingProfile) -> int:
    """买房时点：默认在生育前两年（约 28 岁）；已经过了的则立刻买。"""
    return max(0, max(p.age, CHILD_BIRTH_AGE - 2) - p.age)


def stage_rate(child_age: int) -> int:
    for lo, hi, rate in EDU_RATE:
        if lo <= child_age < hi:
            return rate
    return 0


def annual_mortgage(price: float, down_ratio: float,
                    rate: float = LOAN_RATE, years: int = LOAN_YEARS) -> float:
    """等额本息，返回年供。"""
    loan = price * (1 - down_ratio)
    r = rate / 12
    n = years * 12
    if r == 0:
        return loan / years
    monthly = loan * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return monthly * 12


# ============================================================
# 五个计算函数
# ============================================================

def clothing_cost(p: LivingProfile, years: int) -> list[float]:
    tier = ret_tier(p)
    base = CLOTHING_BASE[p.lifestyle] * CITY_COEF[tier]
    base *= CLOTHING_FREQ[p.clothing_freq]
    base *= CLOTHING_GRADE[p.clothing_grade]
    return [base * adults_at(p, t) * inflation_factor(t) for t in range(years)]


def food_cost(p: LivingProfile, years: int) -> list[float]:
    tier = ret_tier(p)
    monthly = FOOD_BASE[p.lifestyle] * CITY_COEF[tier]
    monthly *= COOKING_COEF[p.cooking]
    if p.extra_food:
        monthly += EXTRA_FOOD[tier]
    return [monthly * 12 * adults_at(p, t) * inflation_factor(t)
            for t in range(years)]


def housing_cost(p: LivingProfile, years: int) -> list[float]:
    tier = ret_tier(p)
    ht = house_type(p)
    buy_t = house_buy_year(p)
    price = HOUSE_PRICE[tier][ht]
    out = []

    for t in range(years):
        infl = inflation_factor(t)

        if p.housing_plan == "已有房":
            cost = HOLDING_COST[tier] * infl

        elif p.housing_plan in ("一直租房", "还没想"):   # 还没想 → 按租房保守估计
            rent = RENT_BASE[tier][ht] * (1 + RENT_GROWTH) ** t
            cost = rent * 12 + RENTER_UTILITY[tier] * infl   # 租客只付水电，物业费房东出

        elif t < buy_t:                                  # 买房前先租房
            rent = RENT_BASE[tier][ht] * (1 + RENT_GROWTH) ** t
            cost = rent * 12 + RENTER_UTILITY[tier] * infl

        else:  # 买房之后
            k = t - buy_t
            cost = 0.0
            if k == 0:
                cost += price * DOWN_PAYMENT          # 首付：买房那一年一个尖峰
            if k < LOAN_YEARS:
                cost += annual_mortgage(price, DOWN_PAYMENT)   # 月供（名义固定）
            # 用 HOLDING_COST 而不是「房价 × 某个百分比」：同一套房，
            # 不管当初买没买、买了几年，每年的物业水电都该是同一个数。
            cost += HOLDING_COST[tier] * infl

        out.append(cost)
    return out


def transport_cost(p: LivingProfile, years: int) -> list[float]:
    tier = ret_tier(p)
    monthly = COMMUTE_BASE[p.retire_commute] * CITY_COEF[tier]
    daily = monthly * 12 * PARTNER_BASE[p.partner]   # 日常出行按人
    travel = TRIP_ANNUAL[p.trip_level]               # 旅行按家庭
    visits = VISIT_HOME_ANNUAL[p.visits_home]        # 探亲按家庭
    return [(daily + travel + visits) * inflation_factor(t) for t in range(years)]


def education_cost(p: LivingProfile, years: int) -> list[float]:
    out = [0.0] * years
    e = EXPECTED_CHILDREN[p.children]
    if e <= 0:
        return out

    # 多孩边际成本递减：1.2 个孩子 ≈ 1 个的 1.16 倍，不是 1.2 倍
    n = 1 + CHILD_MARGINAL * (e - 1) if e >= 1 else e
    coef = CITY_COEF[ret_tier(p)] * LIFESTYLE_EDU[p.lifestyle]

    for t in range(years):
        ca = child_age_at(p, t)
        if 3 <= ca < 22:
            # 教育用独立通胀率，不能用整体 CPI：学费涨得比通胀快
            out[t] = stage_rate(ca) * n * coef * (1 + EDU_INFLATION) ** t
    return out


def total_living_cost(p: LivingProfile, years: int) -> list[float]:
    parts = [
        clothing_cost(p, years),
        food_cost(p, years),
        housing_cost(p, years),
        transport_cost(p, years),
        education_cost(p, years),
    ]
    return [sum(v) for v in zip(*parts)]
