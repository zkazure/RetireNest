"""蒙特卡洛退休模拟：数千条随机路径下的资金耗尽风险。"""

from __future__ import annotations

from simulation.models import (
    BalancePercentile,
    MonteCarloInput,
    MonteCarloResult,
)
from simulation.returns import generate_real_paths
from simulation.statistics import (
    DEPLETION_PERCENTILES,
    RETIREMENT_PERCENTILES,
    percentile,
    percentile_map,
)


def simulate(data: MonteCarloInput) -> MonteCarloResult:
    """按“积累期 + 退休期”逐条路径推进，统计成功率和分位数。

    成功：退休期内任何一年年末余额都不为负。余额为负即视为耗尽，
    但不提前终止路径，保证逐年分位数仍然完整。
    """
    withdrawal = max(0.0, data.annual_retirement_expense - data.monthly_pension * 12)
    total_years = data.years_to_retirement + data.retirement_years
    paths = generate_real_paths(
        seed=data.seed,
        paths=data.paths,
        years=total_years,
        annual_return_pct=data.annual_return_pct,
        volatility_pct=data.volatility_pct,
        inflation_pct=data.inflation_pct,
    )

    balances: list[list[float]] = [[] for _ in range(total_years + 1)]
    terminal: list[float] = []
    depletion_years: list[int] = []

    for path in paths:
        balance = data.current_savings
        balances[0].append(balance)
        depleted = False
        for year, gross in enumerate(path, start=1):
            if year <= data.years_to_retirement:
                balance = balance * gross + data.monthly_contribution * 12
            else:
                balance = balance * gross - withdrawal
            balances[year].append(balance)
            if not depleted and year > data.years_to_retirement and balance < 0:
                depletion_years.append(year - data.years_to_retirement)
                depleted = True
        terminal.append(balance)

    success_rate = (data.paths - len(depletion_years)) / data.paths * 100
    return MonteCarloResult(
        success_rate=success_rate,
        failed_paths=len(depletion_years),
        terminal_balance_percentiles=percentile_map(terminal, RETIREMENT_PERCENTILES),
        depletion_year_percentiles=percentile_map(
            depletion_years,
            DEPLETION_PERCENTILES,
        ),
        balance_percentiles=tuple(
            BalancePercentile(
                year=year,
                p10=percentile(balances[year], 0.1),
                p50=percentile(balances[year], 0.5),
                p90=percentile(balances[year], 0.9),
            )
            for year in range(total_years + 1)
        ),
    )
