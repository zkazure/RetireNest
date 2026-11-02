"""安全提取率：给定退休余额，反推目标成功率下的可提取比例。"""

from __future__ import annotations

from simulation.models import WithdrawalInput, WithdrawalResult
from simulation.returns import generate_real_paths
from simulation.statistics import DEPLETION_PERCENTILES, percentile_map

BISECTION_STEPS = 24
"""24 次二分把区间压到约 6e-8，远小于展示精度。"""


def _evaluate(
    paths: list[list[float]],
    savings: float,
    annual_withdrawal: float,
) -> tuple[float, list[int]]:
    """返回 (成功率 0–1, 耗尽路径的退休后年份)。"""
    successes = 0
    depletions: list[int] = []
    for path in paths:
        balance = savings
        failed = False
        for year, gross in enumerate(path, start=1):
            balance = balance * gross - annual_withdrawal
            if balance < 0:
                depletions.append(year)
                failed = True
                break
        if not failed:
            successes += 1
    return successes / len(paths), depletions


def safe_withdrawal(data: WithdrawalInput) -> WithdrawalResult:
    """二分搜索满足目标成功率的最高提取比例。

    成功率随提取率单调不增，因此二分成立。所有候选比例共用同一组随机
    路径，结果可复现。
    """
    if data.retirement_savings <= 0:
        return WithdrawalResult(
            safe_withdrawal_rate_pct=0.0,
            annual_withdrawal_real=0.0,
            monthly_withdrawal_real=0.0,
            success_rate_at_rate=100.0,
            depletion_year_percentiles={},
        )

    paths = generate_real_paths(
        seed=data.seed,
        paths=data.paths,
        years=data.retirement_years,
        annual_return_pct=data.annual_return_pct,
        volatility_pct=data.volatility_pct,
        inflation_pct=data.inflation_pct,
    )
    target = data.target_success_rate / 100

    rate = 1.0
    ratio, _ = _evaluate(paths, data.retirement_savings, data.retirement_savings * rate)
    if ratio < target:
        low, high = 0.0, 1.0
        for _ in range(BISECTION_STEPS):
            mid = (low + high) / 2
            ratio_mid, _ = _evaluate(
                paths,
                data.retirement_savings,
                data.retirement_savings * mid,
            )
            if ratio_mid >= target:
                low = mid
            else:
                high = mid
        rate = low

    ratio, depletions = _evaluate(
        paths,
        data.retirement_savings,
        data.retirement_savings * rate,
    )
    annual = data.retirement_savings * rate
    return WithdrawalResult(
        safe_withdrawal_rate_pct=rate * 100,
        annual_withdrawal_real=annual,
        monthly_withdrawal_real=annual / 12,
        success_rate_at_rate=ratio * 100,
        depletion_year_percentiles=percentile_map(depletions, DEPLETION_PERCENTILES),
    )
