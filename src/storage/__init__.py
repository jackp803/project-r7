"""Supported E6 storage composition surfaces.

The supported wildcard/export contract remains the Gate B boundary:
``open_sqlite_platform`` only. Gate C OperationalMode symbols stay bound on this
module for explicit-import compatibility with the accepted Shadow composition,
without expanding ``storage.__all__`` or exposing raw SQLite mechanics.
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

__all__ = ["open_sqlite_platform"]
