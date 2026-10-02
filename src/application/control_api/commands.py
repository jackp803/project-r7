"""Durable dispatch reservations and immutable receipts; never financial authority.

Prepare/complete hold short local transactions. Actual owners execute outside
these transactions and must reuse the same command ID with their own atomic
idempotency/CAS. An expired dispatch is reconciled through that owner seam.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets

from application.control_api.auth import _ClosingConnection
from application.platform.resources import require_local_database_volume
import sqlite3


class CommandError(ValueError):
    def __init__(self, code='CONFLICT', *, reason=None):
        self.code = code
        self.reason = code if reason is None else reason
        super().__init__(code)


_FORBIDDEN = {'password', 'secret', 'api_key', 'api_secret', 'access_token', 'refresh_token',
              'private_key', 'authorization', 'cookie', 'credentials', 'sql', 'executable'}


def _json(value):
    stack = [(value, 0)]; count = 0
    while stack:
        item, depth = stack.pop(); count += 1
        if depth > 24 or count > 10000: raise CommandError('INVALID_INPUT')
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or len(key) > 128 or key.casefold() in _FORBIDDEN:
                    raise CommandError('INVALID_INPUT')
                stack.append((child, depth + 1))
        elif isinstance(item, list): stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            if len(item) > 65536 or '\x00' in item: raise CommandError('INVALID_INPUT')
        elif item is None or type(item) is bool: pass
        elif type(item) is int:
            if abs(item) >= 2**63: raise CommandError('INVALID_INPUT')
        else: raise CommandError('INVALID_INPUT')
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    if len(raw.encode('utf-8')) > 65536: raise CommandError('INVALID_INPUT')
    return raw


def _hash(raw): return 'sha256:' + hashlib.sha256(raw.encode('utf-8')).hexdigest()
def _text(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,195}', value):
        raise CommandError('INVALID_INPUT')
    return value


def _stamp(now):
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(0): raise CommandError('INVALID_INPUT')
    return now.isoformat(timespec='microseconds').replace('+00:00', 'Z')


@dataclass(frozen=True)
class CommandClaim:
    command_id: str
    resource: str
    generation: int
    nonce: str
    request_json: str
    lease_deadline: str


class CommandLedger:
    def __init__(self, path, *, namespace, clock=lambda: datetime.now(timezone.utc)):
        if namespace not in ('FIXTURE', 'LOCAL_RESEARCH') or not callable(clock): raise CommandError('INVALID_INPUT')
        self.path = Path(path).absolute(); require_local_database_volume(self.path)
        if self.path.is_symlink(): raise CommandError('INVALID_INPUT')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.namespace, self.clock = namespace, clock
        with self._db() as db:
            migration = Path(__file__).parents[1] / 'migrations/0004_control_commands.sql'
            db.executescript(migration.read_text(encoding='utf-8'))
            db.execute('INSERT OR IGNORE INTO control_namespace VALUES(1,?)', (namespace,))
            if db.execute('SELECT namespace FROM control_namespace WHERE singleton=1').fetchone()[0] != namespace:
                raise CommandError('NAMESPACE_CONFLICT')

    def _db(self):
        db = sqlite3.connect(self.path, timeout=5); db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=5000'); db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return _ClosingConnection(db)

    def prepare(self, *, command_id, operation, resource, actor, expected_revision, actual_revision, arguments):
        for value in (command_id, operation, resource, actor): _text(value)
        for revision in (expected_revision, actual_revision):
            if type(revision) is not int or not 0 <= revision < 2**63: raise CommandError('INVALID_INPUT')
        raw = _json(dict(namespace=self.namespace, command_id=command_id, operation=operation, resource=resource,
                         actor=actor, expected_revision=expected_revision, arguments=arguments))
        with self._db() as db:
            now = self.clock(); current = _stamp(now); deadline = _stamp(now + timedelta(seconds=30))
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM control_commands WHERE command_id=?', (command_id,)).fetchone()
            if row:
                if row['request_json'] != raw or row['request_hash'] != _hash(raw): raise CommandError()
                if row['status'] == 'COMPLETE':
                    if _hash(row['receipt_json']) != row['receipt_hash']: raise CommandError('COMMAND_STORE_CORRUPT')
                    return json.loads(row['receipt_json'])
                if current < row['prepared_at']: raise CommandError('COMMAND_CLOCK_INVALID')
                if row['lease_deadline'] > current: raise CommandError('COMMAND_IN_PROGRESS')
                generation = row['generation'] + 1; nonce = secrets.token_hex(16)
                db.execute('UPDATE control_commands SET generation=?,nonce=?,lease_deadline=?,prepared_at=? WHERE command_id=? AND status=\'PREPARED\'',
                           (generation, nonce, deadline, current, command_id))
            else:
                if expected_revision != actual_revision: raise CommandError(reason='RESOURCE_REVISION_CONFLICT')
                if db.execute("SELECT 1 FROM control_commands WHERE resource=? AND status='PREPARED'", (resource,)).fetchone():
                    raise CommandError('RESOURCE_COMMAND_PENDING')
                if db.execute('SELECT COUNT(*) FROM control_commands').fetchone()[0] >= 100000:
                    raise CommandError('COMMAND_STORE_CAPACITY_REACHED')
                generation = 1; nonce = secrets.token_hex(16)
                db.execute('''INSERT INTO control_commands(command_id,operation,resource,actor,request_json,request_hash,
                    expected_revision,status,generation,nonce,lease_deadline,prepared_at)
                    VALUES(?,?,?,?,?,?,?,'PREPARED',?,?,?,?)''',
                    (command_id, operation, resource, actor, raw, _hash(raw), expected_revision, generation, nonce, deadline, current))
            return CommandClaim(command_id, resource, generation, nonce, raw, deadline)

    def complete(self, claim, receipt):
        if not isinstance(claim, CommandClaim): raise CommandError('INVALID_INPUT')
        raw = _json(receipt)
        with self._db() as db:
            now = _stamp(self.clock())
            changed = db.execute('''UPDATE control_commands SET status='COMPLETE',completed_at=?,receipt_json=?,receipt_hash=?
                WHERE command_id=? AND resource=? AND generation=? AND nonce=? AND request_json=?
                AND status='PREPARED' AND prepared_at<=? AND lease_deadline>?''',
                (now, raw, _hash(raw), claim.command_id, claim.resource, claim.generation, claim.nonce, claim.request_json, now, now))
            if changed.rowcount != 1: raise CommandError('COMMAND_CLAIM_FENCED')
        return json.loads(raw)
