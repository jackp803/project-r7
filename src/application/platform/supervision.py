"""Actual local process generations and heartbeat; no financial permission.

The lock lasts for the complete owner lifetime. SQLite transactions only record
small supervision facts; research work and API/network I/O never hold them.
These facts do not replace E6 consent, E7 preflight or E4/E5 reconciliation.
"""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import threading
import uuid

from application.config import ProductConfig, load_config
from application.control_api.auth import _ClosingConnection
from application.platform.resources import require_local_database_volume
from application.platform.processes import process_alive
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.research.evidence import capture_provenance, stamp


class SupervisionError(RuntimeError):
    pass


def config_hash(config):
    if not isinstance(config, ProductConfig):
        raise ValueError('Validated product configuration required')
    values = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(config).items()}
    raw = json.dumps(values, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def _local_path(path):
    require_local_database_volume(path)
    for current in (*reversed(path.parents), path):
        try:
            information = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(information.st_mode) or getattr(information, 'st_file_attributes', 0) & 0x400:
            raise SupervisionError('SUPERVISION_LOCAL_PATH_REQUIRED')


def _db(path, *, writable=False):
    _local_path(path)
    target = str(path) if writable else path.as_uri() + '?mode=ro'
    db = sqlite3.connect(target, timeout=2, uri=not writable)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=2000')
    if writable:
        db.execute('PRAGMA synchronous=FULL')
    return _ClosingConnection(db)


def process_health(config, role, *, now=None, max_age_seconds=15):
    if role not in ('control', 'research') or type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 60:
        raise ValueError('Bounded process health policy required')
    current = datetime.now(timezone.utc) if now is None else now
    stamp(current)
    path = config.local_data_root / 'process-supervision.sqlite'
    if not path.exists(): return dict(status='NOT_STARTED', financial_authority='NONE')
    try:
        with _db(path) as db:
            row = db.execute('SELECT * FROM process_sessions WHERE role=?', (role,)).fetchone()
        if row is None: return dict(status='NOT_STARTED', financial_authority='NONE')
        result = dict(row)
        result.pop('identity_json')
        heartbeat = datetime.fromisoformat(row['heartbeat_at'].replace('Z', '+00:00'))
        age = (current - heartbeat).total_seconds()
        status = row['state']
        if status == 'RUNNING':
            if config_hash(config) != row['config_hash']: status = 'CONFIG_CHANGED'
            elif age < 0: status = 'CLOCK_REGRESSION'
            elif age > max_age_seconds: status = 'STALE_HEARTBEAT'
            elif not process_alive(row['pid']): status = 'PROCESS_NOT_RUNNING'
            else: status = 'RECENT_HEARTBEAT'
        result.update(status=status, financial_authority='NONE')
        return result
    except (OSError, ValueError, sqlite3.Error, SupervisionError):
        return dict(status='SUPERVISION_STORAGE_FAILURE', financial_authority='NONE')


class ProcessSupervisor:
    def __init__(self, config, role, *, config_path=None, heartbeat_interval=1,
                 clock=lambda: datetime.now(timezone.utc)):
        if role not in ('control', 'research') or not isinstance(config, ProductConfig) or not callable(clock):
            raise ValueError('Actual configured local owner required')
        if (isinstance(heartbeat_interval, bool) or not isinstance(heartbeat_interval, (int, float))
                or not math.isfinite(heartbeat_interval) or not 0.02 <= heartbeat_interval <= 5):
            raise ValueError('Bounded heartbeat interval required')
        self.config, self.role, self.clock = config, role, clock
        self.config_path = None if config_path is None else Path(config_path).absolute()
        self.config_digest = config_hash(config)
        self.path = config.local_data_root / 'process-supervision.sqlite'
        self.scope = ProcessScopeLock(role + ':' + config.product_instance_id, lock_root=operational_lock_root(config))
        self.interval = heartbeat_interval
        self.stop = threading.Event()
        self.failed = False
        self.failure_code = None
        self.thread = None
        self.identity = None

    def _check_profile(self):
        if self.config_path is not None and config_hash(load_config(self.config_path)) != self.config_digest:
            raise SupervisionError('CONFIG_CHANGED')

    def __enter__(self):
        self.scope.__enter__()
        try:
            self._check_profile()
            _local_path(self.path)
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            identity = capture_provenance()
            started = stamp(self.clock())
            token = str(uuid.uuid4())
            with _db(self.path, writable=True) as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.executescript((Path(__file__).parents[1] / 'migrations/0006_process_supervision.sql').read_text(encoding='utf-8'))
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT generation FROM process_generation_counters WHERE role=?', (self.role,)).fetchone()
                generation = 1 if row is None else row['generation'] + 1
                if generation >= 2**63: raise SupervisionError('PROCESS_GENERATION_EXHAUSTED')
                identity.update(schema_version='r7-process-generation-v0.2', role=self.role,
                    product_instance_id=self.config.product_instance_id, pid=os.getpid(), generation=generation,
                    process_generation_id=token, config_hash=self.config_digest, started_at=started,
                    financial_authority='NONE', restart_admission='RECONCILIATION_REQUIRED')
                raw = json.dumps(identity, sort_keys=True, separators=(',', ':'))
                db.execute('INSERT INTO process_generation_counters VALUES(?,?) ON CONFLICT(role) DO UPDATE SET generation=excluded.generation',
                           (self.role, generation))
                db.execute("UPDATE process_session_history SET state='FAILED',ended_at=? WHERE role=? AND ended_at IS NULL", (started, self.role))
                db.execute("INSERT INTO process_session_history VALUES(?,?,?,?,?,NULL,'RUNNING')", (self.role, generation, token, raw, started))
                db.execute("INSERT OR REPLACE INTO process_sessions VALUES(?,?,?,?,?,?,?,?,?,0,'RUNNING')",
                    (self.role, generation, token, self.config.product_instance_id, os.getpid(), self.config_digest, raw, started, started))
            self.identity = identity
            self.thread = threading.Thread(target=self._heartbeats, name='r7-' + self.role + '-heartbeat', daemon=True)
            self.thread.start()
            return self
        except BaseException:
            self.scope.__exit__()
            raise

    def _transition(self, state):
        with _db(self.path, writable=True) as db:
            db.execute('BEGIN IMMEDIATE')
            cursor = db.execute('UPDATE process_sessions SET state=? WHERE role=? AND process_generation_id=?',
                                (state, self.role, self.identity['process_generation_id']))
            if cursor.rowcount != 1: raise SupervisionError('PROCESS_GENERATION_FENCED')
            db.execute('UPDATE process_session_history SET state=?,ended_at=? WHERE process_generation_id=?',
                       (state, stamp(self.clock()), self.identity['process_generation_id']))

    def _fail(self, code):
        self.failure_code = code
        self.stop.set()
        try:
            self._transition(code if code in ('CONFIG_CHANGED', 'CLOCK_REGRESSION') else 'SUPERVISION_STORAGE_FAILURE')
        except (OSError, ValueError, sqlite3.Error, SupervisionError):
            pass  # Failure stays inhibited; never claim a durable write succeeded.
        finally:
            self.failed = True

    def _heartbeats(self):
        while not self.stop.wait(self.interval):
            try:
                self._check_profile()
                now = stamp(self.clock())
                with _db(self.path, writable=True) as db:
                    db.execute('BEGIN IMMEDIATE')
                    row = db.execute('SELECT process_generation_id,heartbeat_at,state FROM process_sessions WHERE role=?', (self.role,)).fetchone()
                    if row is None or row['process_generation_id'] != self.identity['process_generation_id'] or row['state'] != 'RUNNING':
                        raise SupervisionError('PROCESS_GENERATION_FENCED')
                    if now < row['heartbeat_at']:
                        raise SupervisionError('CLOCK_REGRESSION')
                    cursor = db.execute("UPDATE process_sessions SET heartbeat_at=?,heartbeat_sequence=heartbeat_sequence+1 "
                        "WHERE role=? AND process_generation_id=? AND state='RUNNING' AND heartbeat_at<=?",
                        (now, self.role, self.identity['process_generation_id'], now))
                    if cursor.rowcount != 1: raise SupervisionError('PROCESS_GENERATION_OR_CLOCK_INVALID')
            except SupervisionError as error:
                self._fail(str(error))
            except Exception:
                self._fail('SUPERVISION_STORAGE_FAILURE')

    def require_current(self):
        if self.failed: raise SupervisionError(self.failure_code)
        try:
            self._check_profile()
        except Exception:
            self._fail('CONFIG_CHANGED')
            raise SupervisionError('CONFIG_CHANGED') from None
        health = self.health()
        if (self.identity is None or health['status'] != 'RECENT_HEARTBEAT'
                or health.get('process_generation_id') != self.identity['process_generation_id']):
            raise SupervisionError('PROCESS_GENERATION_NOT_CURRENT')

    def health(self, *, now=None):
        return process_health(self.config, self.role, now=self.clock() if now is None else now)

    def __exit__(self, exception_type=None, *_):
        self.stop.set()
        try:
            if self.thread is not None:
                self.thread.join(3)
                if self.thread.is_alive(): raise SupervisionError('HEARTBEAT_STOP_NOT_CONFIRMED')
            if not self.failed:
                try:
                    self._transition('STOPPED' if exception_type is None else 'FAILED')
                except (OSError, ValueError, sqlite3.Error, SupervisionError):
                    self.failed, self.failure_code = True, 'SUPERVISION_STOP_NOT_CONFIRMED'
                    if exception_type is None: raise SupervisionError(self.failure_code) from None
        finally:
            self.scope.__exit__()
