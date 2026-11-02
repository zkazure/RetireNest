"""医疗三态与软性支出的测试。"""

from __future__ import annotations

import pytest

from living.extras import (
    TRIP_COST,
    entertainment_annual,
    soft_annual,
    travel_annual,
    upbringing_annual,
)
from medical import MAJOR, MINOR, costs, event_cost, expected_annual, probabilities


@pytest.mark.parametrize("age", [18, 35, 45, 55, 65, 75, 85, 100])
@pytest.mark.parametrize("sex", ["男", "女"])
def test_三态概率之和为一(age, sex):
    p = probabilities(age, sex)
    assert p.healthy + p.minor + p.major == pytest.approx(1.0)
    assert 0 <= p.major < p.minor < 1


def test_女性大病概率低于男性():
    assert probabilities(60, "女").major < probabilities(60, "男").major


def test_期望支出随年龄上升():
    young = expected_annual(30, "男")
    old = expected_annual(70, "男")
    assert 0 < young < old


def test_大病支出远高于小病():
    table = costs()
    assert table.major > table.minor > table.healthy >= 0


def test_事件支出与非法状态():
    assert event_cost(MINOR) == costs().minor
    assert event_cost(MAJOR) == costs().major
    with pytest.raises(ValueError):
        event_cost("unknown")


@pytest.mark.parametrize("bad", [17, 121, True, 30.5])
def test_年龄越界(bad):
    with pytest.raises(ValueError):
        probabilities(bad, "男")


def test_性别非法():
    with pytest.raises(ValueError):
        probabilities(40, "未知")


def test_旅游按次数计价():
    assert travel_annual(0) == 0
    assert travel_annual(2) == pytest.approx(2 * TRIP_COST)


def test_娱乐按年折算():
    assert entertainment_annual(800) == pytest.approx(9_600)


def test_养育支出分段():
    assert upbringing_annual(1) == pytest.approx(20_000)
    assert upbringing_annual(10) == pytest.approx(12_000)
    assert upbringing_annual(19) == pytest.approx(8_000)
    assert upbringing_annual(25) == 0


def test_软性支出合计():
    assert soft_annual(entertainment_monthly=800, trips=2, child_age=10) == pytest.approx(
        9_600 + 2 * TRIP_COST + 12_000
    )
    assert soft_annual(entertainment_monthly=800, trips=2, child_age=None) == pytest.approx(
        9_600 + 2 * TRIP_COST
    )


def test_负值报错():
    with pytest.raises(ValueError):
        travel_annual(-1)
    with pytest.raises(ValueError):
        entertainment_annual(-1)
