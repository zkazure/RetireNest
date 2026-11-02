"""把多个策略变体并排跑，给前端与 Agent 一份可比较的摘要。"""

from __future__ import annotations

from dataclasses import dataclass
from profile.schema import Profile

from lifecycle.project import project
from lifecycle.simulate import DEFAULT_PATHS, DEFAULT_SEED, simulate
from strategy import PRESET_IDS, apply, get_preset


@dataclass(frozen=True, slots=True)
class VariantSummary:
    preset_id: str
    label: str
    retirement_age: int
    pension_monthly: float
    break_even_age: int | None
    depleted_age: int | None
    final_assets: float
    success_rate: float
    affordable_monthly_expense: float


def compare(
    profile: Profile,
    *,
    preset_ids: tuple[str, ...] = PRESET_IDS,
    paths: int = DEFAULT_PATHS,
    seed: int = DEFAULT_SEED,
) -> tuple[VariantSummary, ...]:
    summaries = []
    for preset_id in preset_ids:
        variant = apply(get_preset(preset_id), profile)
        projection = project(variant)
        simulation = simulate(variant, paths=paths, seed=seed)
        summaries.append(
            VariantSummary(
                preset_id=preset_id,
                label=get_preset(preset_id).label,
                retirement_age=variant.retirement_age,
                pension_monthly=projection.pension_monthly,
                break_even_age=projection.break_even_age,
                depleted_age=projection.depleted_age,
                final_assets=projection.final_assets,
                success_rate=simulation.success_rate,
                affordable_monthly_expense=simulation.affordable_monthly_expense,
            )
        )
    return tuple(summaries)
