"""E7-owned cross-module integration surfaces."""

from .shadow_composition import (
    SHADOW_CAPABILITY_MANIFEST,
    SHADOW_PLANNING_PROFILE,
    ShadowComposition,
    ShadowCompositionError,
    ShadowCycleResult,
    ShadowPlanningEvidence,
)

__all__ = [
    "SHADOW_CAPABILITY_MANIFEST",
    "SHADOW_PLANNING_PROFILE",
    "ShadowComposition",
    "ShadowCompositionError",
    "ShadowCycleResult",
    "ShadowPlanningEvidence",
]
