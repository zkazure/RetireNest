"""养老金参数的测试：计发月数表、快照更新、过期判断、最低缴费年限。"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pension import PensionError
from pension.params import (
    ADJUSTMENT_SNAPSHOT,
    MAX_AGE_DAYS,
    PAYOUT_MONTHS,
    CalculationBaseQuote,
    RatioQuote,
    base_for,
    latest_adjustment,
    minimum_contribution_years,
    payout_months,
    stale,
    upsert_base,
)

BASE_QUOTE = CalculationBaseQuote(
    province="测试省",
    monthly_base=Decimal(8000),
    effective_year=2025,
    source_url="https://example.com/base",
    fetched_at=date(2026, 1, 1),
)


def test_payout_table_official_spots():
    assert PAYOUT_MONTHS[40] == 233
    assert PAYOUT_MONTHS[50] == 195
    assert PAYOUT_MONTHS[55] == 170
    assert PAYOUT_MONTHS[60] == 139
    assert PAYOUT_MONTHS[63] == 117
    assert PAYOUT_MONTHS[70] == 56


def test_payout_months_floors_fractional_age():
    assert payout_months(60 * 12) == 139
    assert payout_months(60 * 12 + 1) == 139
    assert payout_months(60 * 12 + 11) == 139


@pytest.mark.parametrize("age_months", [-1, 39 * 12, 71 * 12])
def test_payout_months_out_of_range(age_months):
    with pytest.raises(PensionError):
        payout_months(age_months)


def test_upsert_replaces_same_province_and_year():
    newer = CalculationBaseQuote(
        province="测试省",
        monthly_base=Decimal(9000),
        effective_year=2025,
        source_url="https://example.com/base-2026",
        fetched_at=date(2026, 2, 1),
    )
    updated = upsert_base(newer, (BASE_QUOTE,))
    assert updated == (newer,)


def test_upsert_appends_unknown_key():
    other = CalculationBaseQuote(
        province="另一省",
        monthly_base=Decimal(7000),
        effective_year=2025,
        source_url="https://example.com/base-other",
        fetched_at=date(2026, 1, 1),
    )
    updated = upsert_base(other, (BASE_QUOTE,))
    assert updated == (BASE_QUOTE, other)


def test_base_for_returns_quote_and_errors_on_missing():
    assert base_for("测试省", 2025, (BASE_QUOTE,)) == Decimal(8000)
    with pytest.raises(PensionError, match="没有"):
        base_for("测试省", 2024, (BASE_QUOTE,))


def test_base_quote_rejects_bad_values():
    with pytest.raises(PensionError, match="省份"):
        CalculationBaseQuote("", 8000, 2025, "https://example.com", date(2026, 1, 1))
    with pytest.raises(PensionError, match="大于 0"):
        CalculationBaseQuote("测试省", 0, 2025, "https://example.com", date(2026, 1, 1))
    with pytest.raises(PensionError, match="https"):
        CalculationBaseQuote("测试省", 8000, 2025, "http://example.com", date(2026, 1, 1))


def test_latest_adjustment_comes_from_snapshot():
    assert latest_adjustment() == Decimal("0.02")


def test_latest_adjustment_picks_newest_year():
    older = RatioQuote(2024, Decimal("0.03"), "https://example.com/a", date(2025, 1, 1))
    newer = RatioQuote(2025, Decimal("0.02"), "https://example.com/b", date(2026, 1, 1))
    assert latest_adjustment((older, newer)) == Decimal("0.02")
    assert latest_adjustment((newer, older)) == Decimal("0.02")


def test_latest_adjustment_empty_is_an_error():
    with pytest.raises(PensionError, match="快照为空"):
        latest_adjustment(())


def test_adjustment_snapshot_is_traceable():
    assert ADJUSTMENT_SNAPSHOT
    for quote in ADJUSTMENT_SNAPSHOT:
        assert quote.source_url.startswith("https://")
        assert isinstance(quote.fetched_at, date)


def test_stale_detection():
    today = date(2026, 6, 1)
    fresh = CalculationBaseQuote(
        "测试省",
        8000,
        2025,
        "https://example.com/base",
        today - timedelta(days=MAX_AGE_DAYS),
    )
    old = CalculationBaseQuote(
        "测试省",
        8000,
        2024,
        "https://example.com/base",
        today - timedelta(days=MAX_AGE_DAYS + 1),
    )
    assert not stale((fresh,), today=today)
    assert stale((old,), today=today) == (old,)


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (2029, Decimal(15)),
        (2030, Decimal("15.5")),
        (2035, Decimal(18)),
        (2039, Decimal(20)),
        (2045, Decimal(20)),
    ],
)
def test_minimum_contribution_years(year, expected):
    assert minimum_contribution_years(year) == expected
