"""E7-owned cross-module integration surfaces."""

from .shadow_composition import (
    SHADOW_CAPABILITY_MANIFEST,
    ShadowComposition,
    ShadowCompositionError,
    ShadowCycleResult,
)

__all__ = [
    "SHADOW_CAPABILITY_MANIFEST",
    "ShadowComposition",
    "ShadowCompositionError",
    "ShadowCycleResult",
]
