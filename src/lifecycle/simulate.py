"""蒙特卡洛：抽收益路径，给出成功率、破产年龄分位与可支撑的生活水平。"""

from __future__ import annotations

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


def _flows(profile: Profile) -> list[tuple[float, float]]:
    """逐年「流入、支出」。流入含工作期工资与退休期养老金，不含投资收益。"""
    pension_annual = pension_monthly(profile) * 12
    flows = []
    for age in range(profile.age, profile.plan_until):
        working = age < profile.retirement_age
        income = profile.monthly_income * 12 if working else pension_annual
        base = profile.monthly_expense * 12 if working else profile.retirement_expense * 12
        flows.append((income, base + expected_annual(age, profile.sex) + yearly_soft(profile, age)))
    return flows


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
        for offset, (income, expense) in enumerate(flows):
            assets = assets * path[offset] + income - expense
            if assets < 0 and depleted is None:
                depleted = start_age + offset
        terminals.append(assets)
        depletions.append(depleted)
    return terminals, depletions


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[index]


def _age_quantile(ages: list[int], q: float) -> int:
    return round(_quantile([float(age) for age in ages], q))


def simulate(
    profile: Profile,
    *,
    paths: int = DEFAULT_PATHS,
    seed: int = DEFAULT_SEED,
    inflation_pct: float = INFLATION_PCT,
    affordable: bool = True,
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

    affordable_monthly = profile.retirement_expense
    if affordable and success < AFFORDABLE_TARGET:
        affordable_monthly = _affordable(profile, gross, target=AFFORDABLE_TARGET)

    return SimulationResult(
        paths=paths,
        success_rate=round(success, 4),
        depleted_p10=_age_quantile(depleted_ages, 0.1) if depleted_ages else None,
        depleted_median=_age_quantile(depleted_ages, 0.5) if depleted_ages else None,
        depleted_p90=_age_quantile(depleted_ages, 0.9) if depleted_ages else None,
        terminal_p10=round(_quantile(terminals, 0.1), 2),
        terminal_median=round(_quantile(terminals, 0.5), 2),
        terminal_p90=round(_quantile(terminals, 0.9), 2),
        affordable_monthly_expense=round(affordable_monthly, 2),
    )


def _affordable(profile: Profile, gross: list[list[float]], *, target: float) -> float:
    """二分找「成功率不低于 target」的最大退休后月支出。"""
    low, high = 0.2, 1.0 * profile.retirement_expense
    for _ in range(12):
        middle = (low + high) / 2
        scaled = _flows_with_expense(profile, middle)
        _, depletions = _run(profile, scaled, gross)
        rate = sum(1 for value in depletions if value is None) / len(depletions)
        if rate >= target:
            low = middle
        else:
            high = middle
    return low


def _flows_with_expense(profile: Profile, retirement_expense: float) -> list[tuple[float, float]]:
    pension_annual = pension_monthly(profile) * 12
    flows = []
    for age in range(profile.age, profile.plan_until):
        working = age < profile.retirement_age
        income = profile.monthly_income * 12 if working else pension_annual
        base = profile.monthly_expense * 12 if working else retirement_expense * 12
        flows.append((income, base + expected_annual(age, profile.sex) + yearly_soft(profile, age)))
    return flows
