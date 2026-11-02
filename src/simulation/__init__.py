"""simulation：蒙特卡洛退休模拟与安全提取率。"""

from simulation.models import (
    BalancePercentile,
    MonteCarloInput,
    MonteCarloResult,
    WithdrawalInput,
    WithdrawalResult,
)
from simulation.monte_carlo import simulate
from simulation.returns import generate_real_paths, return_parameters, sample_real_gross
from simulation.withdrawal import safe_withdrawal

__all__ = [
    "BalancePercentile",
    "MonteCarloInput",
    "MonteCarloResult",
    "WithdrawalInput",
    "WithdrawalResult",
    "generate_real_paths",
    "return_parameters",
    "safe_withdrawal",
    "sample_real_gross",
    "simulate",
]
