"""利率快照的测试：来源完整性、平均值、过期判断。"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from profit import ProfitError
from profit.demand_deposit import DEFAULT_ANNUAL_RATE
from profit.rates import (
    MAX_AGE_DAYS,
    SNAPSHOT,
    RateQuote,
    average_rate,
    is_stale,
)


def test_snapshot_entries_are_traceable():
    assert SNAPSHOT
    for quote in SNAPSHOT:
        assert quote.source_url.startswith("https://")
        assert quote.bank
        assert isinstance(quote.fetched_at, date)


def test_average_of_snapshot_is_current_rate():
    assert average_rate() == Decimal("0.0005")


def test_default_rate_comes_from_snapshot():
    assert DEFAULT_ANNUAL_RATE == average_rate()


def test_average_of_single_quote():
    quote = RateQuote(
        bank="测试银行",
        annual_rate=Decimal("0.0003"),
        source_url="https://example.com/rate",
        fetched_at=date(2026, 1, 1),
    )
    assert average_rate((quote,)) == Decimal("0.0003")


def test_average_quantizes_to_five_decimal_percent():
    rates = [
        RateQuote(
            bank=f"银行{i}",
            annual_rate=Decimal(rate),
            source_url="https://example.com/rate",
            fetched_at=date(2026, 1, 1),
        )
        for i, rate in enumerate(("0.0005", "0.0001", "0.0001"))
    ]
    # (0.05 + 0.01 + 0.01) / 3 = 0.023333..% → 0.000233
    assert average_rate(tuple(rates)) == Decimal("0.000233")


def test_empty_snapshot_is_an_error():
    with pytest.raises(ProfitError, match="快照为空"):
        average_rate(())


def test_stale_detection():
    today = date(2026, 6, 1)
    fresh = RateQuote(
        bank="测试银行",
        annual_rate=Decimal("0.0005"),
        source_url="https://example.com/rate",
        fetched_at=today - timedelta(days=MAX_AGE_DAYS),
    )
    old = RateQuote(
        bank="测试银行",
        annual_rate=Decimal("0.0005"),
        source_url="https://example.com/rate",
        fetched_at=today - timedelta(days=MAX_AGE_DAYS + 1),
    )
    assert not is_stale((fresh,), today=today)
    assert is_stale((old,), today=today)
