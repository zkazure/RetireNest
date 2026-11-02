"""三输入医疗消费预算，以及三态（无病、小病、大病）的期望支出。"""

from .costs import estimate_medical_cost
from .tri_state import (
    MAJOR,
    MINOR,
    TriStateCost,
    TriStateProbability,
    costs,
    event_cost,
    expected_annual,
    probabilities,
)

estimate_medical_costs = estimate_medical_cost

__all__ = [
    "MAJOR",
    "MINOR",
    "TriStateCost",
    "TriStateProbability",
    "costs",
    "estimate_medical_cost",
    "estimate_medical_costs",
    "event_cost",
    "expected_annual",
    "probabilities",
]
