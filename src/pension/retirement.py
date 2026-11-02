"""法定退休年龄。

依据 2024 年 9 月全国人大常委会《关于实施渐进式延迟法定退休年龄的决定》，
2025-01-01 起用 15 年过渡：男职工 60→63、每 4 个月出生延迟 1 个月；原 55 岁的
女职工 55→58、同样每 4 个月延迟 1 个月；原 50 岁的女职工 50→55、每 2 个月延迟
1 个月。

这里按规则算，不抄附表：规则与附表一一对应，抄三十多行更容易抄错，规则还能直接
覆盖 1990 年出生这类过渡期之后的边界。
"""

from __future__ import annotations

from datetime import date

from pension.errors import PensionError

MALE = "男"
FEMALE = "女"
CATEGORIES = ("管理技术", "工人")

# (性别, 岗位): (原法定周岁, 起算出生年, 起算出生月, 每几个月出生延迟 1 个月, 封顶延迟月数)
_RULES: dict[tuple[str, str | None], tuple[int, int, int, int, int]] = {
    (MALE, None): (60, 1965, 1, 4, 36),
    (FEMALE, "管理技术"): (55, 1970, 1, 4, 36),
    (FEMALE, "工人"): (50, 1975, 1, 2, 60),
}


def retirement_age_months(
    birth_date: date,
    gender: str,
    category: str | None = None,
) -> int:
    """法定退休年龄，单位是月，例如 60 岁记作 720。

    男性不需要 category；女性必须给 category（管理技术或工人），因为原法定年龄不同。
    """
    if gender not in (MALE, FEMALE):
        raise PensionError(f"性别只能是“男”或“女”，收到 {gender!r}")
    if gender == FEMALE and category not in CATEGORIES:
        raise PensionError(f"女性必须指定岗位类别（管理技术或工人），收到 {category!r}")
    key = (MALE, None) if gender == MALE else (FEMALE, category)
    base_years, start_year, start_month, step, cap = _RULES[key]
    months_since_start = (birth_date.year - start_year) * 12 + (birth_date.month - start_month)
    delay = 0 if months_since_start < 0 else min(months_since_start // step + 1, cap)
    return base_years * 12 + delay


def retirement_year_month(birth_date: date, age_months: int) -> tuple[int, int]:
    """出生年月加退休年龄，得到退休年月。"""
    if age_months < 0:
        raise PensionError(f"退休年龄不能为负，收到 {age_months} 个月")
    total = birth_date.year * 12 + (birth_date.month - 1) + age_months
    return total // 12, total % 12 + 1
