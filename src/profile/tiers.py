"""档位表：每个选项对应一个计算取值。

取值原则：区间中值；两端开口的档取一个代表值。金额单位为元，月收入与月支出
是当下购买力。档位粒度与界面文案一并放在这里，页面清单只引用 value。
"""

from __future__ import annotations

from dataclasses import dataclass
from profile.errors import ProfileError


@dataclass(frozen=True, slots=True)
class Tier:
    value: str
    label: str
    amount: float
    low: float | None = None
    high: float | None = None


@dataclass(frozen=True, slots=True)
class TierTable:
    name: str
    unit: str
    tiers: tuple[Tier, ...]

    def get(self, value: str) -> Tier:
        for tier in self.tiers:
            if tier.value == value:
                return tier
        raise ProfileError(f"{self.name} 没有选项 {value!r}")

    def options(self) -> tuple[str, ...]:
        return tuple(tier.value for tier in self.tiers)


INCOME = TierTable(
    name="月收入",
    unit="元/月",
    tiers=(
        Tier("lt5k", "5 千以下", 3_500, None, 5_000),
        Tier("5k8k", "5 千到 8 千", 6_500, 5_000, 8_000),
        Tier("8k12k", "8 千到 1.2 万", 10_000, 8_000, 12_000),
        Tier("12k20k", "1.2 万到 2 万", 16_000, 12_000, 20_000),
        Tier("20k30k", "2 万到 3 万", 25_000, 20_000, 30_000),
        Tier("30k50k", "3 万到 5 万", 40_000, 30_000, 50_000),
        Tier("gt50k", "5 万以上", 60_000, 50_000, None),
    ),
)

EXPENSE = TierTable(
    name="月支出",
    unit="元/月",
    tiers=(
        Tier("lt2k", "2 千以下", 1_500, None, 2_000),
        Tier("2k4k", "2 千到 4 千", 3_000, 2_000, 4_000),
        Tier("4k6k", "4 千到 6 千", 5_000, 4_000, 6_000),
        Tier("6k10k", "6 千到 1 万", 8_000, 6_000, 10_000),
        Tier("10k15k", "1 万到 1.5 万", 12_500, 10_000, 15_000),
        Tier("15k25k", "1.5 万到 2.5 万", 20_000, 15_000, 25_000),
        Tier("gt25k", "2.5 万以上", 30_000, 25_000, None),
    ),
)

ASSETS = TierTable(
    name="资产",
    unit="元",
    tiers=(
        Tier("lt10w", "10 万以下", 50_000, None, 100_000),
        Tier("10w30w", "10 万到 30 万", 200_000, 100_000, 300_000),
        Tier("30w50w", "30 万到 50 万", 400_000, 300_000, 500_000),
        Tier("50w100w", "50 万到 100 万", 750_000, 500_000, 1_000_000),
        Tier("100w200w", "100 万到 200 万", 1_500_000, 1_000_000, 2_000_000),
        Tier("200w500w", "200 万到 500 万", 3_500_000, 2_000_000, 5_000_000),
        Tier("gt500w", "500 万以上", 8_000_000, 5_000_000, None),
    ),
)

DEBT = TierTable(
    name="负债",
    unit="元",
    tiers=(
        Tier("none", "没有负债", 0, 0, 0),
        Tier("lt10w", "10 万以下", 50_000, 0, 100_000),
        Tier("10w30w", "10 万到 30 万", 200_000, 100_000, 300_000),
        Tier("30w50w", "30 万到 50 万", 400_000, 300_000, 500_000),
        Tier("50w100w", "50 万到 100 万", 750_000, 500_000, 1_000_000),
        Tier("gt100w", "100 万以上", 1_500_000, 1_000_000, None),
    ),
)

RETIRE_EXPENSE = TierTable(
    name="退休后月支出",
    unit="元/月",
    tiers=(
        Tier("lt2k", "2 千以下", 1_500, None, 2_000),
        Tier("2k4k", "2 千到 4 千", 3_000, 2_000, 4_000),
        Tier("4k6k", "4 千到 6 千", 5_000, 4_000, 6_000),
        Tier("6k10k", "6 千到 1 万", 8_000, 6_000, 10_000),
        Tier("10k15k", "1 万到 1.5 万", 12_500, 10_000, 15_000),
        Tier("gt15k", "1.5 万以上", 20_000, 15_000, None),
    ),
)

RETIRE_AGE = TierTable(
    name="退休年龄",
    unit="岁",
    tiers=(
        Tier("45", "45 岁", 45, 45, 45),
        Tier("50", "50 岁", 50, 50, 50),
        Tier("55", "55 岁", 55, 55, 55),
        Tier("60", "60 岁", 60, 60, 60),
        Tier("63", "63 岁", 63, 63, 63),
        Tier("65", "65 岁", 65, 65, 65),
        Tier("70", "70 岁", 70, 70, 70),
    ),
)

PLAN_UNTIL = TierTable(
    name="规划至年龄",
    unit="岁",
    tiers=tuple(Tier(str(age), f"{age} 岁", age, age, age) for age in (75, 80, 85, 90, 95, 100)),
)

TRAVEL = TierTable(
    name="旅游",
    unit="次/年",
    tiers=(
        Tier("none", "不出远门", 0, 0, 0),
        Tier("once", "一年一次国内", 1, 1, 1),
        Tier("twice", "一年两次国内", 2, 2, 2),
        Tier("three", "一年三次", 3, 3, 3),
        Tier("often", "经常出行", 5, 5, None),
    ),
)

ENTERTAINMENT = TierTable(
    name="娱乐",
    unit="元/月",
    tiers=(
        Tier("low", "省着花", 300, None, 500),
        Tier("mid", "正常", 800, 500, 1_200),
        Tier("high", "舍得花", 1_500, 1_200, None),
    ),
)
"""娱乐月支出为 [假设]，见 docs/data-sources.md §4。"""

CHILDREN = TierTable(
    name="育儿",
    unit="个",
    tiers=(
        Tier("none", "不要孩子", 0, 0, 0),
        Tier("one", "一个孩子", 1, 1, 1),
        Tier("two", "两个孩子", 2, 2, 2),
    ),
)

LIVING_LEVEL = TierTable(
    name="生活水平",
    unit="倍",
    tiers=(
        Tier("frugal", "节俭", 0.8, 0.8, 0.8),
        Tier("comfortable", "舒适", 1.0, 1.0, 1.0),
        Tier("generous", "宽裕", 1.9, 1.9, 1.9),
    ),
)
"""倍数沿用 CIEFR 收入分组的教育支出比值，用于整体支出缩放。"""
