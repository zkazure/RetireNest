"""蒙特卡洛：抽收益路径，给出成功率、破产年龄分位与两个方向的支出预测。"""

from __future__ import annotations

from dataclasses import replace
from profile.derive import account_balance, contribution_index
from profile.schema import Profile

from lifecycle.errors import LifecycleError
from lifecycle.models import SimulationResult
from lifecycle.project import INFLATION_PCT, pension_monthly, yearly_soft
from medical.tri_state import expected_annual
from portfolio import combine
from simulation.returns import generate_real_paths

MAX_PATHS = 20_000
DEFAULT_PATHS = 1_000
DEFAULT_SEED = 42
AFFORDABLE_TARGET = 0.9
"""两个预测共用的目标成功率，与「可支撑支出」的历史口径一致。"""

BISECTION_STEPS = 20
"""20 次二分在 1000 万的收入区间上也能把误差压到 10 元以内。"""

INCOME_CAP = 10_000_000
"""反推收入的上界，与命令层 income 输入的 max 一致。"""

EXPENSE_RATIO_CAP = 20.0
"""支出缩放倍数的上界，避免极端画像把区间拉得过大。"""


def _flows(profile: Profile) -> list[tuple[float, float]]:
    """逐年「流入、支出」。流入含工作期工资与退休期养老金，不含投资收益。"""
    return _flows_with_level(profile, 1.0)


def _flows_with_level(profile: Profile, ratio: float) -> list[tuple[float, float]]:
    """把基础生活支出按 ratio 缩放，医疗与软性支出保持原值。"""
    pension_annual = pension_monthly(profile) * 12
    flows = []
    for age in range(profile.age, profile.plan_until):
        working = age < profile.retirement_age
        inflow = profile.monthly_income * 12 if working else pension_annual
        base = profile.monthly_expense if working else profile.retirement_expense
        flows.append(
            (
                inflow,
                base * ratio * 12
                + expected_annual(age, profile.sex)
                + yearly_soft(profile, age),
            )
        )
    return flows


def _with_income(profile: Profile, monthly_income: float) -> Profile:
    """换一个工作期月收入，并同步重算缴费指数与个人账户余额。"""
    params = profile.pension
    return replace(
        profile,
        monthly_income=monthly_income,
        pension=replace(
            params,
            index=contribution_index(monthly_income, params.base_wage),
            account_balance=account_balance(monthly_income, params.years),
        ),
    )


def _run(
    profile: Profile,
    flows: list[tuple[float, float]],
    gross: list[list[float]],
) -> tuple[list[float], list[int | None]]:
    """跑完全部路径，返回每条路径的期末资产与破产年龄。"""
    terminals: list[float] = []
    depletions: list[int | None] = []
    start_age = profile.age
    for path in gross:
        assets = float(profile.net_assets)
        depleted: int | None = None
        for offset, (inflow, expense) in enumerate(flows):
            assets = assets * path[offset] + inflow - expense
            if assets < 0 and depleted is None:
                depleted = start_age + offset
        terminals.append(assets)
        depletions.append(depleted)
    return terminals, depletions


def _rate(profile: Profile, flows: list[tuple[float, float]], gross: list[list[float]]) -> float:
    """资产任何一年不为负的路径占比。"""
    _, depletions = _run(profile, flows, gross)
    return sum(1 for value in depletions if value is None) / len(depletions)


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[index]


def _age_quantile(ages: list[int], q: float) -> int:
    return round(_quantile([float(age) for age in ages], q))


def _required_income(
    profile: Profile,
    gross: list[list[float]],
    *,
    target: float,
) -> float | None:
    """二分「维持现有支出所需的最低工作期月收入」。

    支出计划不动；候选收入会重算养老金，因此成功率随收入单调不减。
    收入封顶后仍达不到目标时返回 None，由展示层说明超出可测算范围。
    """

    def rate(monthly_income: float) -> float:
        candidate = _with_income(profile, monthly_income)
        return _rate(candidate, _flows(candidate), gross)

    high = max(profile.monthly_income, 1.0)
    if rate(high) < target:
        while high < INCOME_CAP:
            high = min(high * 2, INCOME_CAP)
            if rate(high) >= target:
                break
        else:
            return None
    if rate(0.0) >= target:
        return 0.0

    low = 0.0
    for _ in range(BISECTION_STEPS):
        middle = (low + high) / 2
        if rate(middle) >= target:
            high = middle
        else:
            low = middle
    return high


def _affordable_level(
    profile: Profile,
    gross: list[list[float]],
    *,
    target: float,
) -> float:
    """二分「收入不变时能支撑的支出倍数」。

    工作期与退休后的基础生活支出按同一倍数缩放，医疗与软性支出不变。
    """

    def rate(ratio: float) -> float:
        return _rate(profile, _flows_with_level(profile, ratio), gross)

    if rate(0.0) < target:
        return 0.0
    high = 1.0
    while rate(high) >= target and high < EXPENSE_RATIO_CAP:
        high = min(high * 2, EXPENSE_RATIO_CAP)
    if rate(high) >= target:
        return EXPENSE_RATIO_CAP

    low = 0.0
    for _ in range(BISECTION_STEPS):
        middle = (low + high) / 2
        if rate(middle) >= target:
            low = middle
        else:
            high = middle
    return low


def simulate(
    profile: Profile,
    *,
    paths: int = DEFAULT_PATHS,
    seed: int = DEFAULT_SEED,
    inflation_pct: float = INFLATION_PCT,
    required: bool = True,
) -> SimulationResult:
    if isinstance(paths, bool) or not isinstance(paths, int) or not 100 <= paths <= MAX_PATHS:
        raise LifecycleError(f"路径数需在 100 到 {MAX_PATHS} 之间。")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**31 - 1:
        raise LifecycleError("随机种子需在 0 到 2^31-1 之间。")

    assumption = combine(profile.allocations)
    years = profile.plan_until - profile.age
    gross = generate_real_paths(
        seed=seed,
        paths=paths,
        years=years,
        annual_return_pct=assumption.annual_return_pct,
        volatility_pct=assumption.volatility_pct,
        inflation_pct=inflation_pct,
    )
    flows = _flows(profile)
    terminals, depletions = _run(profile, flows, gross)
    success = sum(1 for value in depletions if value is None) / paths
    depleted_ages = [age for age in depletions if age is not None]

    level = _affordable_level(profile, gross, target=AFFORDABLE_TARGET)
    required_income = (
        _required_income(profile, gross, target=AFFORDABLE_TARGET) if required else None
    )

    return SimulationResult(
        paths=paths,
        success_rate=round(success, 4),
        depleted_p10=_age_quantile(depleted_ages, 0.1) if depleted_ages else None,
        depleted_median=_age_quantile(depleted_ages, 0.5) if depleted_ages else None,
        depleted_p90=_age_quantile(depleted_ages, 0.9) if depleted_ages else None,
        terminal_p10=round(_quantile(terminals, 0.1), 2),
        terminal_median=round(_quantile(terminals, 0.5), 2),
        terminal_p90=round(_quantile(terminals, 0.9), 2),
        affordable_monthly_expense=round(profile.retirement_expense * level, 2),
        affordable_working_expense=round(profile.monthly_expense * level, 2),
        required_monthly_income=(
            None if required_income is None else round(required_income, 2)
        ),
    )
