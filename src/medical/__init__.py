"""三输入医疗消费预算原型。"""

from .costs import estimate_medical_cost

estimate_medical_costs = estimate_medical_cost

__all__ = ["estimate_medical_cost", "estimate_medical_costs"]
