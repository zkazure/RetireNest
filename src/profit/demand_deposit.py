"""银行活期存款收益计算。

只做单利一次性计息：

    日利率   = 年利率 ÷ 360
    利息     = 本金 × 日利率 × 实际天数
    期末本息 = 本金 + 利息

口径：
- 日利率按年利率除以 360 折算，这是人民币业务的通行规则，不是 365；
- 天数算头不算尾，即 (结束日期 - 起始日期)，结束日期当天不计息；
- 金额与利率全程用 Decimal，利息只在最后一步按分四舍五入，中间不截断。

不做的事，以及为什么：
- 不复利：真实活期按季结息、利息并入本金，季度复利一年只差几毛钱，
  因此本期按单利处理；若要和银行对账单逐笔对齐，再改为按季结息。
- 不建模利率变化：跨降息周期由调用方分段计算后相加。
- 不支持多账户汇总：一次计算只对应一笔存款。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

DAYS_PER_YEAR = Decimal(360)
"""人民币日利率按 360 天折算，不是 365。"""

DEFAULT_ANNUAL_RATE = Decimal("0.0005")
"""缺省年利率 0.05%，即 2025 年 5 月六大行活期挂牌利率，可按银行公告覆盖。"""

CENT = Decimal("0.01")
_DAILY_RATE_QUANTUM = Decimal("0.0000000001")


class ProfitError(ValueError):
    """参数不满足计算前提时抛出。"""


@dataclass(frozen=True, slots=True)
class DemandDeposit:
    """一笔活期存款的输入。

    principal 与 annual_rate 接受 Decimal、int 或字符串；float 会被拒绝，
    因为二进制浮点会带出 1 分钱级的误差。
    """

    principal: Decimal | int | str
    start_date: date
    end_date: date
    annual_rate: Decimal | int | str | None = None

    def __post_init__(self) -> None:
        principal = _to_decimal(self.principal, "本金")
        rate = (
            DEFAULT_ANNUAL_RATE
            if self.annual_rate is None
            else _to_decimal(self.annual_rate, "年利率")
        )
        if principal <= 0:
            raise ProfitError(f"本金必须大于 0，收到 {principal}")
        if principal != principal.quantize(CENT):
            raise ProfitError(f"本金最多保留两位小数（到分），收到 {principal}")
        if rate < 0:
            raise ProfitError(f"年利率不能为负，收到 {rate}")
        if self.end_date <= self.start_date:
            raise ProfitError(f"结束日期 {self.end_date} 必须晚于起始日期 {self.start_date}")
        object.__setattr__(self, "principal", principal)
        object.__setattr__(self, "annual_rate", rate)


@dataclass(frozen=True, slots=True)
class DemandDepositResult:
    """一次活期收益计算的结果，字段都是可追溯的中间量或终值。"""

    principal: Decimal
    annual_rate: Decimal
    days: int
    interest: Decimal
    total: Decimal

    @property
    def daily_rate(self) -> Decimal:
        """日利率，仅供展示；利息按未截断的利率计算，避免二次舍入。"""
        return (self.annual_rate / DAYS_PER_YEAR).quantize(_DAILY_RATE_QUANTUM, ROUND_HALF_UP)


def calculate(deposit: DemandDeposit) -> DemandDepositResult:
    """计算一笔活期存款的利息与期末本息。

    天数算头不算尾，即 (end_date - start_date).days；利息只在最后一步
    按分四舍五入，中间不截断。
    """
    days = (deposit.end_date - deposit.start_date).days
    interest = (deposit.principal * deposit.annual_rate / DAYS_PER_YEAR * days).quantize(
        CENT, ROUND_HALF_UP
    )
    return DemandDepositResult(
        principal=deposit.principal,
        annual_rate=deposit.annual_rate,
        days=days,
        interest=interest,
        total=deposit.principal + interest,
    )


def _to_decimal(value: Decimal | int | str, name: str) -> Decimal:
    if isinstance(value, float):
        raise ProfitError(f"{name}请用 Decimal 或字符串传入，float 会带出浮点误差")
    if isinstance(value, bool):
        raise ProfitError(f"{name}不接受布尔值")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ProfitError(f"{name}不是合法数字：{value!r}") from exc
