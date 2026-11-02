"""输入数据结构与校验。"""

from dataclasses import dataclass

from living.constants import (
    CITY_TIER,
    CLOTHING_FREQ,
    CLOTHING_GRADE,
    COMMUTE_BASE,
    COOKING_COEF,
    EXPECTED_CHILDREN,
    LIFE_EXPECTANCY,
    LIFESTYLE_EDU,
    PARTNER_BASE,
    TRIP_ANNUAL,
    VISIT_HOME_ANNUAL,
)
from living.errors import LivingCostError


@dataclass
class LivingProfile:
    # ---- A. 现状 ----
    age: int
    city: str
    monthly_expense: float          # 每月总支出（已含通勤/正装/外卖）
    child_age_now: int | None = None  # 现有孩子现在的年龄；没有孩子填 None

    # ---- B. 退休打算 ----
    retire_age: int = 60
    life_expectancy: int = LIFE_EXPECTANCY   # 测算到多大，默认 85，用户可改
    partner: str = "还没想好"        # 独自生活 / 有伴侣 / 还没想好
    children: str = "还没想好"       # 想要 / 不想要 / 还没想好
    housing_plan: str = "还没想"     # 一直租房 / 买房自住 / 已有房 / 还没想
    lifestyle: str = "舒适"          # 节俭 / 舒适 / 宽裕
    retire_city: str = ""            # 空 = 与现在同城

    # ---- C. 退休后偏好 ----
    clothing_freq: str = "一般"      # 很少 / 一般 / 经常
    clothing_grade: str = "品牌"     # 平价 / 品牌 / 奢侈品
    cooking: str = "一半一半"         # 主要自己做 / 一半一半 / 主要外食
    extra_food: bool = False         # 三餐外饮食需求
    retire_commute: str = "公交地铁"  # 公交地铁 / 打车 / 自己开车 / 骑车步行
    trip_level: str = "偶尔国内"      # 很少出门 / 偶尔国内 / 经常旅行
    visits_home: str = "一年一两次"   # 不回 / 一年一两次 / 三次以上

    def __post_init__(self) -> None:
        """输入校验。dataclass 会自动调用，前台传错值立刻报错，绝不带着错值往下算。"""
        # 1) 枚举字段必须逐字匹配。差一个字就会走进错误的 if 分支，算出假数字。
        enums = {
            "partner":        (self.partner,        PARTNER_BASE),
            "children":       (self.children,       EXPECTED_CHILDREN),
            "housing_plan":   (self.housing_plan,   {"一直租房", "买房自住", "已有房", "还没想"}),
            "lifestyle":      (self.lifestyle,      LIFESTYLE_EDU),
            "clothing_freq":  (self.clothing_freq,  CLOTHING_FREQ),
            "clothing_grade": (self.clothing_grade, CLOTHING_GRADE),
            "cooking":        (self.cooking,        COOKING_COEF),
            "retire_commute": (self.retire_commute, COMMUTE_BASE),
            "trip_level":     (self.trip_level,     TRIP_ANNUAL),
            "visits_home":    (self.visits_home,    VISIT_HOME_ANNUAL),
        }
        for name, (value, allowed) in enums.items():
            if value not in allowed:      # dict 的 in 判断的是键，正好是合法取值
                raise LivingCostError(f"{name} 只能是 {list(allowed)}，收到 {value!r}")

        # 2) 城市必须在表里，否则 city_tier() 会静默按二线算
        if self.city not in CITY_TIER:
            raise LivingCostError(
                f"city {self.city!r} 不在支持列表里（共 {len(CITY_TIER)} 个）")
        if self.retire_city and self.retire_city not in CITY_TIER:
            raise LivingCostError(f"retire_city {self.retire_city!r} 不在支持列表里")

        # 3) 数值范围：年龄顺序反了会让循环少跑或多跑，直接算错
        if not (18 <= self.age < self.retire_age < self.life_expectancy <= 120):
            raise LivingCostError(
                f"年龄顺序不合理：现在 {self.age}、退休 {self.retire_age}、"
                f"测算到 {self.life_expectancy}")
        if self.monthly_expense <= 0:
            raise LivingCostError(
                f"monthly_expense 必须 > 0，收到 {self.monthly_expense}")
        if not isinstance(self.extra_food, bool):
            raise LivingCostError(
                f"extra_food 必须是 True/False，收到 {self.extra_food!r}")

        # 4) 现有孩子：年龄要和用户年龄对得上
        if self.child_age_now is not None:
            if not (0 <= self.child_age_now <= 50):
                raise LivingCostError(
                    f"child_age_now 应为 0~50，收到 {self.child_age_now}")
            if self.age - self.child_age_now < 15:
                raise LivingCostError(
                    f"你 {self.age} 岁而孩子 {self.child_age_now} 岁 —— 生育时不到 15 岁")
