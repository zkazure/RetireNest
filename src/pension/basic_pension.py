"""城镇职工基本养老金：基础养老金 + 个人账户养老金。

只算“退休时点”的月养老金，口径来自国发〔2005〕38 号：

    基础养老金   = 计发基数 × (1 + 平均缴费指数) ÷ 2 × 缴费年限 × 1%
    个人账户养老金 = 个人账户储存额 ÷ 计发月数

口径与取舍：
- 计发基数由调用方传入，本模块不内置全国参数表；省份与年度的查表在 params.py。
- 缴费年限用 Decimal 年，允许小数，不取整——年限是乘数，取整会系统性改变结果。
- 个人账户只按退休时点的余额算，不做记账利率复利，也不做未来缴费的 8% 累积。
- 金额保留到分，中间不截断；替代率保留四位小数。

不做的事，以及为什么：
- 不做视同缴费年限：1996 年前的口径复杂，由调用方折算进缴费年限。
- 不做跨省转移、补缴、断缴：折算成等效缴费年限后传入。
- 不做弹性提前/延迟退休：只按法定年龄算，提前与延迟的收益差留给情景对比。
- 不做折现：折现率是政策选择，缺口模块自己折，这里只给名义现金流。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pension.decimals import CENT, to_decimal
from pension.errors import PensionError
from pension.params import latest_adjustment, payout_months
from pension.retirement import retirement_age_months

INDEX_MIN = Decimal("0.6")
INDEX_MAX = Decimal("3.0")
"""缴费工资下限 60%、上限 300% 社平工资，对应平均缴费指数的合法区间。"""

REPLACEMENT_QUANTUM = Decimal("0.0001")
"""替代率保留四位小数，即 0.01%。"""

MAX_CONTRIBUTION_YEARS = 50
"""超过 50 年基本可以断定是输入错误，直接拒绝，避免把缺口算歪。"""


@dataclass(frozen=True, slots=True)
class BasicPensionInput:
    """按月领取养老金的测算输入。

    Decimal 参数接受 Decimal、int 或字符串，float 会被拒绝。
    """

    birth_date: date
    gender: str
    contribution_years: Decimal | int | str
    average_index: Decimal | int | str
    account_balance: Decimal | int | str
    calculation_base: Decimal | int | str
    category: str | None = None
    prior_monthly_wage: Decimal | int | str | None = None
    annual_adjustment: Decimal | int | str | None = None

    def __post_init__(self) -> None:
        years = to_decimal(self.contribution_years, "缴费年限")
        index = to_decimal(self.average_index, "平均缴费指数")
        balance = to_decimal(self.account_balance, "个人账户储存额")
        base = to_decimal(self.calculation_base, "计发基数")
        if years <= 0:
            raise PensionError(f"缴费年限必须大于 0，收到 {years}")
        if years > MAX_CONTRIBUTION_YEARS:
            raise PensionError(f"缴费年限超过 {MAX_CONTRIBUTION_YEARS} 年，疑似输入错误：{years}")
        if not INDEX_MIN <= index <= INDEX_MAX:
            raise PensionError(f"平均缴费指数必须在 {INDEX_MIN}~{INDEX_MAX} 之间，收到 {index}")
        if balance < 0:
            raise PensionError(f"个人账户储存额不能为负，收到 {balance}")
        if base <= 0:
            raise PensionError(f"计发基数必须大于 0，收到 {base}")
        wage = None
        if self.prior_monthly_wage is not None:
            wage = to_decimal(self.prior_monthly_wage, "退休前月工资")
            if wage <= 0:
                raise PensionError(f"退休前月工资必须大于 0，收到 {wage}")
        adjustment = (
            latest_adjustment()
            if self.annual_adjustment is None
            else to_decimal(self.annual_adjustment, "年调整率")
        )
        if adjustment < 0:
            raise PensionError(f"年调整率不能为负，收到 {adjustment}")
        object.__setattr__(self, "contribution_years", years)
        object.__setattr__(self, "average_index", index)
        object.__setattr__(self, "account_balance", balance)
        object.__setattr__(self, "calculation_base", base)
        object.__setattr__(self, "prior_monthly_wage", wage)
        object.__setattr__(self, "annual_adjustment", adjustment)


@dataclass(frozen=True, slots=True)
class BasicPensionResult:
    """一次测算的结果，字段都是可追溯的中间量或终值。"""

    retirement_age_months: int
    payout_months: int
    basic_pension: Decimal
    account_pension: Decimal
    total: Decimal
    annual_adjustment: Decimal
    replacement_rate: Decimal | None
    calculation_base: Decimal
    average_index: Decimal
    contribution_years: Decimal

    def monthly_at(self, months_after_retirement: int) -> Decimal:
        """退休后第 n 个月的名义月养老金，每满一年按调整率上调一次。

        n < 12 时与退休当月相同；调整率是名义值，不做通胀扣减。
        """
        if months_after_retirement < 0:
            raise PensionError(f"月数不能为负，收到 {months_after_retirement}")
        years = months_after_retirement // 12
        grown = self.total * (Decimal(1) + self.annual_adjustment) ** years
        return grown.quantize(CENT, ROUND_HALF_UP)


def calculate(inp: BasicPensionInput) -> BasicPensionResult:
    """算退休当月的基础养老金、个人账户养老金与合计，保留到分。"""
    age_months = retirement_age_months(inp.birth_date, inp.gender, inp.category)
    months = payout_months(age_months)
    basic = (
        inp.calculation_base
        * (Decimal(1) + inp.average_index)
        / 2
        * inp.contribution_years
        * Decimal("0.01")
    ).quantize(CENT, ROUND_HALF_UP)
    account = (inp.account_balance / months).quantize(CENT, ROUND_HALF_UP)
    total = basic + account
    replacement = None
    if inp.prior_monthly_wage is not None:
        replacement = (total / inp.prior_monthly_wage).quantize(REPLACEMENT_QUANTUM, ROUND_HALF_UP)
    return BasicPensionResult(
        retirement_age_months=age_months,
        payout_months=months,
        basic_pension=basic,
        account_pension=account,
        total=total,
        annual_adjustment=inp.annual_adjustment,
        replacement_rate=replacement,
        calculation_base=inp.calculation_base,
        average_index=inp.average_index,
        contribution_years=inp.contribution_years,
    )
