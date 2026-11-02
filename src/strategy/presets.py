"""五个预设人生策略。

一个预设只描述「相对用户的默认活法改什么」：改退休年龄、改支出档、改育儿、
改资产配比。没写的维度保持用户自己的选择，所以预设可以叠加在任意画像上。
"""

from __future__ import annotations

from dataclasses import dataclass, field

STEADY = "steady"
DINK = "dink"
FIRE = "fire"
ONE_CHILD = "one_child"
FRUGAL = "frugal"
PRESET_IDS = (STEADY, DINK, FIRE, ONE_CHILD, FRUGAL)


@dataclass(frozen=True, slots=True)
class Preset:
    id: str
    label: str
    summary: str
    retirement_age_delta: int = 0
    retirement_expense_factor: float = 1.0
    travel_trips: float | None = None
    entertainment: str | None = None
    children: int | None = None
    allocation: dict[str, float] = field(default_factory=lambda: {"high": 0.3, "mid": 0.5, "low": 0.2})
    """未写的维度用 None，表示沿用用户自己的选择。"""


PRESETS: dict[str, Preset] = {
    STEADY: Preset(
        id=STEADY,
        label="安然一生",
        summary="按法定年龄退休，收支平衡，风险中等。作为其它策略的对照基准。",
        travel_trips=1,
        entertainment="mid",
    ),
    DINK: Preset(
        id=DINK,
        label="丁克",
        summary="不育儿，把育儿预算转成旅行与投资，提前三年退休。",
        retirement_age_delta=-3,
        travel_trips=2,
        entertainment="mid",
        children=0,
        allocation={"high": 0.5, "mid": 0.4, "low": 0.1},
    ),
    FIRE: Preset(
        id=FIRE,
        label="早退 FIRE",
        summary="提前十年退休，支出降一档，靠高权益比例撑住长期现金流。",
        retirement_age_delta=-10,
        retirement_expense_factor=0.8,
        travel_trips=1,
        entertainment="low",
        allocation={"high": 0.6, "mid": 0.3, "low": 0.1},
    ),
    ONE_CHILD: Preset(
        id=ONE_CHILD,
        label="养娃一孩",
        summary="一个孩子从出生养到大学毕业，退休延后两年，支出比基准高一成。",
        retirement_age_delta=2,
        retirement_expense_factor=1.1,
        travel_trips=1,
        entertainment="mid",
        children=1,
    ),
    FRUGAL: Preset(
        id=FRUGAL,
        label="低耗稳健",
        summary="压缩一切可选支出，几乎全放低风险，求的是确定性而不是收益率。",
        retirement_expense_factor=0.7,
        travel_trips=0,
        entertainment="low",
        allocation={"high": 0.0, "mid": 0.2, "low": 0.8},
    ),
}


def get_preset(preset_id: str) -> Preset:
    from strategy.errors import StrategyError

    preset = PRESETS.get(preset_id)
    if preset is None:
        raise StrategyError(f"未知策略：{preset_id!r}")
    return preset
