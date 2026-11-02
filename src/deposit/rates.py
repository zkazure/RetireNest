"""银行存款利率快照。

为什么是快照而不是实时抓取：挂牌利率由各家银行自主定价、各自公告，没有统一
接口，运行时去抓既不稳定也不可追溯。所以这里只保存人工核对过的记录，每条都
带来源链接和抓取时间；默认利率取快照的等权平均。

更新流程：在 src/ 下运行 `uv run python tools/fetch_rates.py` 拿候选值，对照
银行公告核对后改这里的 SNAPSHOT，再跑一遍测试。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from deposit.errors import DepositError

RATE_QUANTUM = Decimal("0.000001")
"""利率量化到 0.0001 个百分点，避免平均值带出无意义的尾数。"""

MAX_AGE_DAYS = 90
"""超过这个天数未复核，快照就视为过期；降息周期里复核频率要更高。"""


@dataclass(frozen=True, slots=True)
class RateQuote:
    """一家银行的活期挂牌利率，年利率用小数表示，0.05% 记作 0.0005。"""

    bank: str
    annual_rate: Decimal
    source_url: str
    fetched_at: date
    effective_date: date | None = None


SNAPSHOT: tuple[RateQuote, ...] = (
    RateQuote(
        bank="工商银行",
        annual_rate=Decimal("0.0005"),
        source_url="https://www.icbc.com.cn/column/1438058341686722587.html",
        fetched_at=date(2026, 11, 2),
        effective_date=date(2025, 5, 20),
    ),
    RateQuote(
        bank="建设银行",
        annual_rate=Decimal("0.0005"),
        source_url="https://wealth.ccb.com/chn/personal/interestv3/rmbdeposit.shtml",
        fetched_at=date(2026, 11, 2),
    ),
    RateQuote(
        bank="招商银行",
        annual_rate=Decimal("0.0005"),
        source_url="https://fin.paas.cmbchina.com/fininfo/interestrate",
        fetched_at=date(2026, 11, 2),
    ),
)


def average_rate(quotes: tuple[RateQuote, ...] = SNAPSHOT) -> Decimal:
    """等权算术平均。

    等权不等于按存款规模加权，样本也偏向大行；它回答的是"这几家挂牌利率
    的中位数是多少"，不能当成全国平均来宣传。
    """
    if not quotes:
        raise DepositError("利率快照为空，无法计算平均利率")
    total = sum((quote.annual_rate for quote in quotes), Decimal(0))
    return (total / len(quotes)).quantize(RATE_QUANTUM, ROUND_HALF_UP)


def is_stale(
    quotes: tuple[RateQuote, ...] = SNAPSHOT,
    today: date | None = None,
    max_age_days: int = MAX_AGE_DAYS,
) -> bool:
    """任一记录超过 max_age_days 天未复核即为过期。"""
    today = date.today() if today is None else today
    return any((today - quote.fetched_at).days > max_age_days for quote in quotes)
