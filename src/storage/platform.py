from __future__ import annotations

from pathlib import Path

from registry import StrategyPlatformService
from registry.ports import StrategyCompatibilityBoundary

from ._sqlite_registry import _open_authorized_store


def open_sqlite_platform(
    path: str | Path,
    *,
    compatibility_boundary: StrategyCompatibilityBoundary | None = None,
    research_namespace: str | None = None,
    product_assessment_boundary=None,
    lifecycle_boundary=None,
) -> StrategyPlatformService:
    """Return the supported E6 SQLite-backed platform service.

    This is the supported composition boundary for downstream project code. It does
    not return or expose the mutable SQLite connection or authoritative RegistryStore.
    Raw SQLite mechanics live in ``storage._sqlite_registry`` and are internal to the
    trusted-process modular-monolith implementation.
    """

    store = _open_authorized_store(path)
    try:
        if research_namespace is not None: store.bind_research_namespace(research_namespace)
    except BaseException:
        store.close()
        raise
    service=StrategyPlatformService(store, compatibility_boundary)
    service._product_assessment_boundary=product_assessment_boundary
    store._lifecycle_boundary=lifecycle_boundary
    return service


__all__ = ["open_sqlite_platform"]
