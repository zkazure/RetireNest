"""软性支出：娱乐、旅游与育儿养育。

这三项在图上都属于「用户可以少花、也可以多花」的部分，与 `living` 里按
统计口径算的衣食住行分开：前者由档位决定，后者由城市与家庭规模决定。
"""

from __future__ import annotations

TRIP_COST = 2_500.0
"""[假设] 每人每次跨省游：文旅部 2025 年人均每次 966 元含大量短途，退休后按 2500 估。"""

UPBRINGING = (
    (0, 2, 20_000.0),
    (3, 5, 15_000.0),
    (6, 11, 12_000.0),
    (12, 17, 12_000.0),
    (18, 21, 8_000.0),
)
"""(孩子年龄下限, 上限, 年养育支出) —— 不含教育费，教育在 living/constants.py 的 EDU_RATE。"""


def travel_annual(trips: float) -> float:
    if trips < 0:
        raise ValueError("旅游次数不能为负。")
    return trips * TRIP_COST


def entertainment_annual(monthly: float) -> float:
    if monthly < 0:
        raise ValueError("娱乐支出不能为负。")
    return monthly * 12


def upbringing_annual(child_age: int) -> float:
    """孩子 0–21 岁的年养育支出；超出范围返回 0。"""
    for start, end, amount in UPBRINGING:
        if start <= child_age <= end:
            return amount
    return 0.0


def soft_annual(*, entertainment_monthly: float, trips: float, child_age: int | None) -> float:
    """一年软性支出合计；没有孩子时传 None。"""
    total = entertainment_annual(entertainment_monthly) + travel_annual(trips)
    if child_age is not None:
        total += upbringing_annual(child_age)
    return total
