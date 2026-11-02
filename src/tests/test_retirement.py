"""法定退休年龄规则的测试。"""

from datetime import date

import pytest

from pension import PensionError
from pension.retirement import retirement_age_months, retirement_year_month


@pytest.mark.parametrize(
    ("birth_date", "gender", "category", "expected"),
    [
        # 男：1965-01 起每 4 个月出生延迟 1 个月，封顶 63 岁
        (date(1964, 12, 1), "男", None, 720),
        (date(1965, 1, 1), "男", None, 721),
        (date(1965, 5, 1), "男", None, 722),
        (date(1976, 8, 1), "男", None, 755),
        (date(1976, 9, 1), "男", None, 756),
        (date(1990, 1, 1), "男", None, 756),
        # 女、管理技术：1970-01 起每 4 个月延迟 1 个月，封顶 58 岁
        (date(1969, 12, 1), "女", "管理技术", 660),
        (date(1970, 1, 1), "女", "管理技术", 661),
        (date(1981, 9, 1), "女", "管理技术", 696),
        (date(1990, 1, 1), "女", "管理技术", 696),
        # 女、工人：1975-01 起每 2 个月延迟 1 个月，封顶 55 岁
        (date(1974, 12, 1), "女", "工人", 600),
        (date(1975, 1, 1), "女", "工人", 601),
        (date(1975, 2, 1), "女", "工人", 601),
        (date(1975, 3, 1), "女", "工人", 602),
        (date(1984, 10, 1), "女", "工人", 659),
        (date(1984, 11, 1), "女", "工人", 660),
        (date(1990, 1, 1), "女", "工人", 660),
    ],
)
def test_retirement_age_rules(birth_date, gender, category, expected):
    assert retirement_age_months(birth_date, gender, category) == expected


def test_male_ignores_category():
    assert retirement_age_months(date(1965, 1, 1), "男", "工人") == 721


def test_invalid_gender_is_rejected():
    with pytest.raises(PensionError, match="性别"):
        retirement_age_months(date(1970, 1, 1), "其他")


def test_female_requires_category():
    with pytest.raises(PensionError, match="岗位类别"):
        retirement_age_months(date(1970, 1, 1), "女")
    with pytest.raises(PensionError, match="岗位类别"):
        retirement_age_months(date(1970, 1, 1), "女", "其他")


def test_retirement_year_month():
    assert retirement_year_month(date(1965, 3, 1), 721) == (2025, 4)
    assert retirement_year_month(date(1970, 1, 1), 660) == (2025, 1)
    assert retirement_year_month(date(1975, 12, 1), 601) == (2026, 1)


def test_retirement_year_month_rejects_negative_age():
    with pytest.raises(PensionError):
        retirement_year_month(date(1970, 1, 1), -1)
