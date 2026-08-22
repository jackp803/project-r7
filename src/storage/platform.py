from __future__ import annotations

from pathlib import Path

from registry import StrategyPlatformService
from registry.ports import StrategyCompatibilityBoundary

from ._sqlite_registry import _open_authorized_store


def open_sqlite_platform(
    path: str | Path,
    *,
    compatibility_boundary: StrategyCompatibilityBoundary | None = None,
) -> StrategyPlatformService:
    """Return the supported E6 SQLite-backed platform service.

    This is the supported composition boundary for downstream project code. It does
    not return or expose the mutable SQLite connection or authoritative RegistryStore.
    Raw SQLite mechanics live in ``storage._sqlite_registry`` and are internal to the
    trusted-process modular-monolith implementation.
    """

    store = _open_authorized_store(path)
    return StrategyPlatformService(store, compatibility_boundary)


__all__ = ["open_sqlite_platform"]
