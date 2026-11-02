"""inflation：名义金额与实际购买力换算。"""

from inflation.convert import convert
from inflation.models import (
    NOMINAL_TO_REAL,
    REAL_TO_NOMINAL,
    InflationInput,
    InflationResult,
)

__all__ = [
    "NOMINAL_TO_REAL",
    "REAL_TO_NOMINAL",
    "InflationInput",
    "InflationResult",
    "convert",
]
