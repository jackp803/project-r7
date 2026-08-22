"""Supported E6 storage composition surface.

Only the safe SQLite-backed platform factory is public. Raw connections, migrations,
and authoritative writer/store mechanics are intentionally internal implementation
symbols under ``storage._sqlite_registry``.
"""

from .platform import open_sqlite_platform

__all__ = ["open_sqlite_platform"]
