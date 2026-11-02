"""pension：退休后的确定性收入，目前只覆盖城镇职工基本养老保险。"""

from pension.basic_pension import BasicPensionInput, BasicPensionResult, calculate
from pension.errors import PensionError
from pension.params import (
    ADJUSTMENT_SNAPSHOT,
    CALC_BASE_SNAPSHOT,
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
from pension.retirement import (
    CATEGORIES,
    FEMALE,
    MALE,
    retirement_age_months,
    retirement_year_month,
)

__all__ = [
    "ADJUSTMENT_SNAPSHOT",
    "CALC_BASE_SNAPSHOT",
    "CATEGORIES",
    "FEMALE",
    "MALE",
    "MAX_AGE_DAYS",
    "PAYOUT_MONTHS",
    "BasicPensionInput",
    "BasicPensionResult",
    "CalculationBaseQuote",
    "PensionError",
    "RatioQuote",
    "base_for",
    "calculate",
    "latest_adjustment",
    "minimum_contribution_years",
    "payout_months",
    "retirement_age_months",
    "retirement_year_month",
    "stale",
    "upsert_base",
]
