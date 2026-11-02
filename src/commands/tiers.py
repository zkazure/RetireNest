"""把 `type="tier"` 的输入换成计算取值。

manifest 里带的是选项（value/label/amount），命令的 handler 需要数字。
解析集中在这里，领域函数因此继续只接受数字，不必知道档位的存在。
"""

from __future__ import annotations

from profile import tiers as profile_tiers
from profile.errors import ProfileError

from commands.models import InputSpec, TierOption


def options(table: profile_tiers.TierTable) -> tuple[TierOption, ...]:
    """由档位表生成 manifest 选项。"""
    return tuple(
        TierOption(value=tier.value, label=tier.label, amount=tier.amount)
        for tier in table.tiers
    )


def amount(spec: InputSpec, value: str) -> float:
    """取选项对应的数值；选项不存在时抛 `ProfileError`。"""
    for tier in spec.tiers:
        if tier.value == value:
            return tier.amount
    raise ProfileError(f"{spec.question} 没有选项 {value!r}")
