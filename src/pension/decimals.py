"""Decimal 的输入转换与金额精度。

params 与 basic_pension 都要把外部输入转成 Decimal，放一处避免两份口径漂移。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pension.errors import PensionError

CENT = Decimal("0.01")
"""金额保留到分。"""


def to_decimal(value: Decimal | int | str, name: str) -> Decimal:
    """把 Decimal、int 或字符串转成 Decimal；float 直接拒绝。

    float 会带出 1 分钱级的二进制误差，宁可让调用方显式传入字符串。
    """
    if isinstance(value, float):
        raise PensionError(f"{name}请用 Decimal 或字符串传入，float 会带出浮点误差")
    if isinstance(value, bool):
        raise PensionError(f"{name}不接受布尔值")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise PensionError(f"{name}不是合法数字：{value!r}") from exc
