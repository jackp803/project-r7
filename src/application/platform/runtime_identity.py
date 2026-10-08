"""Coherent read-only facts for an already running local runtime generation.

This snapshot is neither qualification evidence nor continuing authority. Its
consumer must separately verify the release and fence every runtime effect.
Reading never creates storage, migrates, attaches a worker or renews a heartbeat.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from types import MappingProxyType
from typing import Mapping
import uuid

from application.config import ProductConfig
from application.platform.processes import process_alive
from application.platform.supervision import (
    SupervisionError, _db, _local_path, _recognized_supervision_schemas,
    _require_supervision_schema, config_hash,
)
from application.research.evidence import stamp


class RuntimeIdentityUnavailable(RuntimeError):
    """No validated current runtime snapshot; never a start/admission decision."""


@dataclass(frozen=True)
class RuntimeIdentitySnapshot:
    identity: Mapping[str, str | int]
    heartbeat_at: str
    heartbeat_sequence: int
    observed_at: str


_SOURCE_KEYS = frozenset((
    'executable_revision', 'implementation_hash', 'worktree', 'os', 'os_version',
    'architecture', 'python', 'execution', 'provider_requests', 'credentials',
    'capital', 'github_compute', 'schema_version', 'role', 'product_instance_id',
    'pid', 'generation', 'process_generation_id', 'config_hash', 'started_at',
    'financial_authority', 'restart_admission',
))
_NATIVE_KEYS = _SOURCE_KEYS | {'build_hash', 'distribution_profile'}
_INTEGER_KEYS = frozenset(('pid', 'generation', 'provider_requests'))
_HASH = re.compile(r'sha256:[0-9a-f]{64}\Z')
_REVISION = re.compile(r'[0-9a-f]{40}\Z')


def _invalid():
    raise RuntimeIdentityUnavailable('RUNTIME_IDENTITY_INVALID')


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _time(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp(parsed) != value:
        _invalid()
    return parsed


def _positive(value):
    return type(value) is int and 1 <= value < 2**63


def _identity(row, history):
    raw = row['identity_json']
    if raw != history['identity_json']:
        _invalid()
    value = json.loads(raw, object_pairs_hook=_pairs,
        parse_constant=lambda _: _invalid())
    if not isinstance(value, dict) or frozenset(value) not in (_SOURCE_KEYS, _NATIVE_KEYS):
        _invalid()
    if any(type(item) is not (int if key in _INTEGER_KEYS else str)
           or type(item) is str and not 1 <= len(item) <= 1024
           for key, item in value.items()):
        _invalid()
    if not _REVISION.fullmatch(value['executable_revision']) or not _HASH.fullmatch(value['implementation_hash']):
        _invalid()
    if (not _HASH.fullmatch(value['config_hash']) or not _positive(value['generation'])
            or not _positive(value['pid']) or value['pid'] >= 2**(32 if os.name == 'nt' else 31)):
        _invalid()
    token = uuid.UUID(value['process_generation_id'])
    if token.version != 4 or str(token) != value['process_generation_id']:
        _invalid()
    required = dict(schema_version='r7-process-generation-v0.2', role='runtime',
        execution='LOCAL', provider_requests=0, credentials='NONE', capital='NONE',
        github_compute='NOT_USED', financial_authority='NONE', restart_admission='RECONCILIATION_REQUIRED')
    if any(type(value[key]) is not type(expected) or value[key] != expected for key, expected in required.items()):
        _invalid()
    if value['worktree'] not in ('CLEAN', 'DIRTY', 'UNAVAILABLE'):
        _invalid()
    if 'build_hash' in value:
        if (not _HASH.fullmatch(value['build_hash']) or value['worktree'] != 'UNAVAILABLE'
                or value['distribution_profile'] != 'r7-native-distribution-v0.2'):
            _invalid()
    for key in ('role', 'generation', 'process_generation_id', 'product_instance_id', 'pid', 'config_hash', 'started_at'):
        if type(value[key]) is not type(row[key]) or value[key] != row[key]:
            _invalid()
    for key in ('role', 'generation', 'process_generation_id', 'started_at'):
        if type(history[key]) is not type(row[key]) or history[key] != row[key]:
            _invalid()
    return value


def read_runtime_identity(config, *, now=None, max_age_seconds=15):
    """Return immutable observed facts or deny; all SQLite reads share a snapshot."""
    if (not isinstance(config, ProductConfig) or type(max_age_seconds) is not int
            or not 1 <= max_age_seconds <= 60):
        raise ValueError('Validated configuration and bounded freshness policy required')
    current = datetime.now(timezone.utc) if now is None else now
    observed = stamp(current)
    path = config.local_data_root / 'process-supervision.sqlite'
    try:
        _local_path(path)
        if not path.exists():
            raise RuntimeIdentityUnavailable('RUNTIME_NOT_STARTED')
        root = Path(__file__).parents[1] / 'migrations'
        legacy = (root / '0006_process_supervision.sql').read_text(encoding='utf-8')
        additive = (root / '0008_runtime_process_supervision.sql').read_text(encoding='utf-8')
        _, schema = _recognized_supervision_schemas(legacy, additive)
        commitment = 'sha256:' + hashlib.sha256(additive.replace('\r\n', '\n').encode('utf-8')).hexdigest()
        with _db(path) as db:
            db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN')
            _require_supervision_schema(db, schema)
            receipts = [tuple(row) for row in db.execute('SELECT migration,sha256 FROM process_supervision_schema')]
            if receipts != [('0008_runtime_process_supervision', commitment)]:
                _invalid()
            size = db.execute("SELECT length(CAST(identity_json AS BLOB)) FROM process_sessions WHERE role='runtime'").fetchone()
            if size is None:
                raise RuntimeIdentityUnavailable('RUNTIME_NOT_STARTED')
            if type(size[0]) is not int or not 1 <= size[0] <= 16 * 1024:
                _invalid()
            row = db.execute("SELECT * FROM process_sessions WHERE role='runtime'").fetchone()
            counter = db.execute("SELECT generation FROM process_generation_counters WHERE role='runtime'").fetchone()
            history = db.execute('SELECT * FROM process_session_history WHERE role=? AND generation=? '
                'AND length(CAST(identity_json AS BLOB)) BETWEEN 1 AND 16384', ('runtime', row['generation'])).fetchone()
            if counter is None or history is None or counter[0] != row['generation']:
                _invalid()
            value = _identity(row, history)
            if row['state'] != 'RUNNING' or history['state'] != 'RUNNING' or history['ended_at'] is not None:
                raise RuntimeIdentityUnavailable('RUNTIME_NOT_RUNNING')
            if value['product_instance_id'] != config.product_instance_id or value['config_hash'] != config_hash(config):
                raise RuntimeIdentityUnavailable('RUNTIME_CONFIG_CHANGED')
            start, heartbeat = _time(row['started_at']), _time(row['heartbeat_at'])
            if (heartbeat < start or current < heartbeat or (current - heartbeat).total_seconds() > max_age_seconds
                    or type(row['heartbeat_sequence']) is not int or not 0 <= row['heartbeat_sequence'] < 2**63):
                raise RuntimeIdentityUnavailable('RUNTIME_HEARTBEAT_INVALID')
            if not process_alive(value['pid']):
                raise RuntimeIdentityUnavailable('RUNTIME_PROCESS_NOT_RUNNING')
            return RuntimeIdentitySnapshot(MappingProxyType(value), row['heartbeat_at'], row['heartbeat_sequence'], observed)
    except RuntimeIdentityUnavailable:
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError, sqlite3.Error, SupervisionError):
        raise RuntimeIdentityUnavailable('RUNTIME_IDENTITY_STORAGE_OR_FORMAT_INVALID') from None
