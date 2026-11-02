"""养老金的参数快照。

计发基数与年度调整比例都不是可以写死的常量：前者由各省级人社部门每年公布，
后者由人社部、财政部每年发通知。所以这里保存带来源和日期的人工核对记录，并提供
查表、更新、过期判断三个纯函数——运行时绝不联网，也绝不写文件。

更新流程：拿到新公告后，用 upsert_base() 生成新的元组，打印出来贴回本文件的
CALC_BASE_SNAPSHOT，再跑一遍测试；调整率同理改 ADJUSTMENT_SNAPSHOT。函数只负责
产出新数据，落表这一步留给人，保证每条记录都经过核对。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pension.decimals import to_decimal
from pension.errors import PensionError

PAYOUT_MONTHS: dict[int, int] = {
    40: 233,
    41: 230,
    42: 226,
    43: 223,
    44: 220,
    45: 216,
    46: 212,
    47: 208,
    48: 204,
    49: 199,
    50: 195,
    51: 190,
    52: 185,
    53: 180,
    54: 175,
    55: 170,
    56: 164,
    57: 158,
    58: 152,
    59: 145,
    60: 139,
    61: 132,
    62: 125,
    63: 117,
    64: 109,
    65: 101,
    66: 93,
    67: 84,
    68: 75,
    69: 65,
    70: 56,
}
"""国发〔2005〕38 号附表：退休年龄（周岁）对应的个人账户计发月数。"""

MAX_AGE_DAYS = 365
"""计发基数一年公布一次，调整率每年七八月发通知，超过一年未复核就提示。"""


def payout_months(age_months: int) -> int:
    """按周岁取计发月数。

    附表只有整数周岁，延迟退休带来的零头月份向下取整（60 岁 1 个月按 60 岁档取 139）。
    零头月份没有官方口径，向下取整会略微低估个人账户养老金，属于有意的保守取舍。
    """
    if age_months < 0:
        raise PensionError(f"退休年龄不能为负，收到 {age_months} 个月")
    age = age_months // 12
    if age not in PAYOUT_MONTHS:
        raise PensionError(f"计发月数表只覆盖 40~70 周岁，收到 {age_months} 个月（{age} 周岁）")
    return PAYOUT_MONTHS[age]


@dataclass(frozen=True, slots=True)
class CalculationBaseQuote:
    """一个省份某一年度的基本养老金计发基数。"""

    province: str
    monthly_base: Decimal | int | str
    effective_year: int
    source_url: str
    fetched_at: date

    def __post_init__(self) -> None:
        if not self.province:
            raise PensionError("省份不能为空")
        base = to_decimal(self.monthly_base, "计发基数")
        if base <= 0:
            raise PensionError(f"计发基数必须大于 0，收到 {base}")
        if not self.source_url.startswith("https://"):
            raise PensionError(f"来源链接必须以 https:// 开头，收到 {self.source_url!r}")
        if not 1900 <= self.effective_year <= 2100:
            raise PensionError(f"生效年份不在合理范围：{self.effective_year}")
        object.__setattr__(self, "monthly_base", base)


CALC_BASE_SNAPSHOT: tuple[CalculationBaseQuote, ...] = ()
"""计发基数快照，初始为空。

计发基数由各省每年单独公布，没有统一口径，未经人工核对的数字不写入任何一条；
首次使用前用 upsert_base() 生成记录并落表。
"""


def base_for(
    province: str,
    year: int,
    quotes: tuple[CalculationBaseQuote, ...] = CALC_BASE_SNAPSHOT,
) -> Decimal:
    """按省份与公布年度取计发基数；没有记录就报错，不猜、不外推。"""
    for quote in quotes:
        if quote.province == province and quote.effective_year == year:
            return quote.monthly_base
    raise PensionError(
        f"计发基数快照里没有 {province} {year} 年度的记录，请先用 upsert_base() 补充"
    )


def upsert_base(
    quote: CalculationBaseQuote,
    quotes: tuple[CalculationBaseQuote, ...] = CALC_BASE_SNAPSHOT,
) -> tuple[CalculationBaseQuote, ...]:
    """同省同年度的记录替换，否则追加；返回新元组，不改入参。"""
    key = (quote.province, quote.effective_year)
    updated: list[CalculationBaseQuote] = []
    replaced = False
    for existing in quotes:
        if (existing.province, existing.effective_year) == key:
            updated.append(quote)
            replaced = True
        else:
            updated.append(existing)
    if not replaced:
        updated.append(quote)
    return tuple(updated)


@dataclass(frozen=True, slots=True)
class RatioQuote:
    """一年度全国退休人员基本养老金的总体调整比例。"""

    year: int
    ratio: Decimal | int | str
    source_url: str
    fetched_at: date

    def __post_init__(self) -> None:
        ratio = to_decimal(self.ratio, "调整比例")
        if ratio < 0:
            raise PensionError(f"调整比例不能为负，收到 {ratio}")
        if not self.source_url.startswith("https://"):
            raise PensionError(f"来源链接必须以 https:// 开头，收到 {self.source_url!r}")
        if not 1900 <= self.year <= 2100:
            raise PensionError(f"年度不在合理范围：{self.year}")
        object.__setattr__(self, "ratio", ratio)


ADJUSTMENT_SNAPSHOT: tuple[RatioQuote, ...] = (
    RatioQuote(
        year=2025,
        ratio=Decimal("0.02"),
        source_url="https://www.gov.cn/zhengce/zhengceku/202507/content_7031449.htm",
        fetched_at=date(2026, 11, 2),
    ),
)
"""截至目前最后一次公布的全国总体调整比例：2025 年度 2.0%。

2026 年度通知在记录日尚未发布，发布后按 README 的流程用 upsert 更新。
"""


def latest_adjustment(quotes: tuple[RatioQuote, ...] = ADJUSTMENT_SNAPSHOT) -> Decimal:
    """取年度最新的一条调整比例；快照为空直接报错，不返回 0。"""
    if not quotes:
        raise PensionError("调整率快照为空，无法取得默认调整比例")
    return max(quotes, key=lambda quote: quote.year).ratio


def stale(
    quotes: Sequence[CalculationBaseQuote | RatioQuote],
    today: date | None = None,
    max_age_days: int = MAX_AGE_DAYS,
) -> tuple[CalculationBaseQuote | RatioQuote, ...]:
    """超过 max_age_days 天未复核的记录；刚好到期不算过期。"""
    today = date.today() if today is None else today
    return tuple(quote for quote in quotes if (today - quote.fetched_at).days > max_age_days)


def minimum_contribution_years(receiving_year: int) -> Decimal:
    """按月领取职工养老金的最低缴费年限。

    2029 年及以前 15 年；2030 年起每年提高 6 个月，2039 年及以后 20 年。
    """
    if receiving_year <= 2029:
        return Decimal(15)
    if receiving_year >= 2039:
        return Decimal(20)
    return Decimal(15) + Decimal("0.5") * (receiving_year - 2029)
