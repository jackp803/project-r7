"""Supported E6 storage composition surfaces.

Only safe service/factory surfaces are public. Raw SQLite connections, migrations,
and authoritative writer/store mechanics remain internal implementation symbols.
"""

from .operational_mode import (
    OPERATIONAL_MODES,
    OperationalModeAuthorityError,
    OperationalModeConflictError,
    OperationalModeError,
    OperationalModeRecord,
    OperationalModeRecovery,
    OperationalModeStore,
    OperationalModeValidationError,
    ShadowCheckpoint,
    open_operational_mode_store,
)
from .platform import open_sqlite_platform

__all__ = [
    "OPERATIONAL_MODES",
    "OperationalModeAuthorityError",
    "OperationalModeConflictError",
    "OperationalModeError",
    "OperationalModeRecord",
    "OperationalModeRecovery",
    "OperationalModeStore",
    "OperationalModeValidationError",
    "ShadowCheckpoint",
    "open_operational_mode_store",
    "open_sqlite_platform",
]
