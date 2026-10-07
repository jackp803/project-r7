"""E6 append-only simulation intents, effects and recoverable publication outbox.

The broker/domain owners compute outside transactions. A complete operation
atomically saves the next broker/runtime state and the domain publication bundle.
After a crash, publication reuses that bundle instead of executing effects again.
No recovered state, receipt or process generation grants entry permission.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping

from brokers.paper import PaperBroker
from brokers.paper_state import canonical_state_json
from execution.models import require_utc
from ._sqlite_registry import _apply_migrations, _connect
from .runtime import _reject_provider_native_fields
from ._runtime_validation import _reject_noncanonical
from .runtime_models import RuntimeConflictError, RuntimeValidationError

_HASH = re.compile(r'sha256:[0-9a-f]{64}')
_BINDING = {'namespace', 'mode', 'strategy_id', 'strategy_version',
            'strategy_content_hash', 'implementation_hash', 'config_hash',
            'risk_policy_hash', 'paper_policy_hash'}
_SECRET_FIELDS = {'api_key', 'api_secret', 'secret', 'password', 'authorization',
                  'access_token', 'refresh_token', 'private_key', 'credentials', 'cookie'}


def _invalid(message):
    raise RuntimeValidationError('PAPER_CHECKPOINT_INVALID', message)


def _conflict(message):
    raise RuntimeConflictError('PAPER_OPERATION_CONFLICT', message)


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 256 or '\x00' in value:
        _invalid('Bounded nonempty Paper identity required')
    return value


def _stamp(value):
    if not isinstance(value, datetime): _invalid('Aware UTC observation required')
    try: require_utc(value, 'observation time')
    except ValueError as exc: _invalid(str(exc))
    return value.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _digest(raw):
    return 'sha256:' + hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _json(value):
    # Bounded pure JSON only. Financial floats and credential/provider-native
    # fields cannot become durable simulation evidence.
    stack, count = [(value, 0)], 0
    while stack:
        node, depth = stack.pop(); count += 1
        if depth > 32 or count > 300_000: _invalid('Paper payload complexity limit')
        if isinstance(node, Mapping):
            for key, child in node.items():
                _text(key)
                if key.casefold() in _SECRET_FIELDS: _invalid('Credential fields forbidden in Paper payload')
                stack.append((child, depth + 1))
        elif isinstance(node, list): stack.extend((child, depth + 1) for child in node)
        elif isinstance(node, str):
            if len(node) > 4096 or '\x00' in node: _invalid('Paper payload text limit')
        elif node is None or type(node) is bool: pass
        elif type(node) is int:
            if abs(node) > 2**63 - 1: _invalid('Paper integer limit')
        else: _invalid('Paper payload requires pure JSON; financial numbers use decimal strings')
    _reject_provider_native_fields(value)
    _reject_noncanonical(value)
    try: return canonical_state_json(value)
    except ValueError as exc: _invalid(str(exc))


def _state(value):
    if not isinstance(value, Mapping) or set(value) != {'broker', 'runtime'} or not isinstance(value['runtime'], dict):
        _invalid('Paper checkpoint requires explicit broker and runtime facts')
    raw = _json(value)
    try: PaperBroker.from_state(value['broker'])
    except ValueError as exc: _invalid(str(exc))
    return raw


def _binding(value):
    if not isinstance(value, Mapping) or set(value) != _BINDING:
        _invalid('Exact Paper run subject/source/config/policy binding required')
    if ((value['namespace'], value['mode']) not in
            (('FIXTURE', 'ACCELERATED_FIXTURE'), ('LOCAL_RESEARCH', 'REAL_TIME'))):
        _invalid('Fixture and real elapsed Paper namespaces cannot mix')
    for name in ('strategy_id', 'strategy_version'): _text(value[name])
    for name in _BINDING - {'namespace', 'mode', 'strategy_id', 'strategy_version'}:
        if not isinstance(value[name], str) or not _HASH.fullmatch(value[name]): _invalid('Exact Paper binding hash required')
    return _json(value)


def _read_json(raw, expected_hash):
    if _digest(raw) != expected_hash: _invalid('Stored Paper payload hash mismatch')
    try: value = json.loads(raw)
    except (ValueError, RecursionError) as exc: _invalid('Stored Paper JSON corrupt')
    if _json(value) != raw: _invalid('Stored Paper serialization is not canonical')
    return value


@dataclass(frozen=True)
class PaperOperation:
    run_id: str
    operation_id: str
    status: str
    base_revision: int
    base_state_json: str
    request_json: str
    checkpoint_revision: int | None = None
    state_json: str | None = None
    outcome_json: str | None = None
    effect_hash: str | None = None

    @property
    def base_state(self): return json.loads(self.base_state_json)
    @property
    def request(self): return json.loads(self.request_json)
    @property
    def state(self): return None if self.state_json is None else json.loads(self.state_json)
    @property
    def outcome(self): return None if self.outcome_json is None else json.loads(self.outcome_json)


@dataclass(frozen=True)
class PaperProcessRecovery:
    run_id: str
    binding_json: str
    revision: int
    state_json: str
    status: str
    pending_operations: tuple[str, ...]
    process_generation: int

    @property
    def binding(self): return json.loads(self.binding_json)
    @property
    def state(self): return json.loads(self.state_json)


class PaperProcessJournal:
    def __init__(self, connection): self._db = connection
    def close(self): self._db.close()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    @contextmanager
    def _write(self):
        if self._db.in_transaction: _invalid('Paper operation requires an idle writer')
        try:
            self._db.execute('BEGIN IMMEDIATE')
            yield
            self._db.commit()
        except sqlite3.Error as exc:
            self._db.rollback()
            raise RuntimeValidationError('PAPER_DURABLE_WRITE_FAILED', 'Paper write rolled back') from exc
        except BaseException:
            self._db.rollback()
            raise

    def _run(self, run_id):
        _text(run_id)
        row = self._db.execute('SELECT * FROM paper_process_runs WHERE run_id=?', (run_id,)).fetchone()
        if row is None: _invalid('Unknown Paper run')
        _binding(_read_json(row['binding_json'], row['binding_hash']))
        return row

    def _checkpoint(self, run_id, revision=None):
        if revision is None:
            row = self._db.execute('SELECT * FROM paper_process_checkpoints WHERE run_id=? ORDER BY revision DESC LIMIT 1', (run_id,)).fetchone()
        else:
            row = self._db.execute('SELECT * FROM paper_process_checkpoints WHERE run_id=? AND revision=?', (run_id, revision)).fetchone()
        if row is None: _invalid('Paper checkpoint missing')
        # Stored states were owner-validated before their write. Under a writer
        # transaction only verify retained bytes; E4 validation runs on recovery
        # after releasing the read snapshot, and on new effects before BEGIN.
        _read_json(row['state_json'], row['state_hash'])
        return row

    def create_run(self, run_id, binding, initial_state, *, now):
        _text(run_id); binding_raw = _binding(binding); state_raw = _state(initial_state); at = _stamp(now)
        with self._write():
            existing = self._db.execute('SELECT * FROM paper_process_runs WHERE run_id=?', (run_id,)).fetchone()
            if existing:
                first = self._checkpoint(run_id, 0)
                if existing['binding_json'] != binding_raw or first['state_json'] != state_raw:
                    _conflict('Existing Paper run identity or initial state changed')
            else:
                self._db.execute('INSERT INTO paper_process_runs VALUES (?,?,?,?)',
                                 (run_id, binding_raw, _digest(binding_raw), at))
                self._db.execute('INSERT INTO paper_process_checkpoints VALUES (?,0,NULL,?,?,?)',
                                 (run_id, state_raw, _digest(state_raw), at))
        return self.recover(run_id)

    def operation(self, run_id, operation_id):
        self._run(run_id); _text(operation_id)
        row = self._db.execute('SELECT * FROM paper_process_operations WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()
        if row is None: return None
        _read_json(row['request_json'], row['request_hash'])
        base = self._checkpoint(run_id, row['base_revision'])
        effect = self._db.execute('SELECT * FROM paper_process_effects WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()
        if effect is None:
            return PaperOperation(run_id, operation_id, 'PREPARED', row['base_revision'], base['state_json'], row['request_json'])
        checkpoint = self._checkpoint(run_id, effect['checkpoint_revision'])
        if checkpoint['operation_id'] != operation_id or effect['checkpoint_revision'] != row['base_revision'] + 1:
            _invalid('Paper operation checkpoint lineage corrupt')
        _read_json(effect['outcome_json'], effect['outcome_hash'])
        expected = self._effect_hash(run_id, operation_id, checkpoint['state_hash'], effect['outcome_hash'])
        if expected != effect['effect_hash']: _invalid('Paper operation effect hash mismatch')
        publication = self._db.execute('SELECT * FROM paper_process_publications WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()
        if publication is not None and publication['effect_hash'] != expected: _invalid('Paper publication hash mismatch')
        return PaperOperation(run_id, operation_id, 'PUBLISHED' if publication else 'APPLIED', row['base_revision'],
            base['state_json'], row['request_json'], checkpoint['revision'], checkpoint['state_json'],
            effect['outcome_json'], effect['effect_hash'])

    def _require_process(self, run_id, process_generation):
        if type(process_generation) is not int or process_generation < 0:
            _invalid('Explicit Paper process generation required')
        current = self._db.execute('SELECT COALESCE(MAX(generation),0) FROM paper_process_generations WHERE run_id=?', (run_id,)).fetchone()[0]
        if current != process_generation: _conflict('Paper effect writer belongs to a stale process generation')

    def prepare(self, run_id, operation_id, request, *, expected_revision, now, process_generation=0):
        if not isinstance(request, Mapping): _invalid('Paper operation request must be an object')
        _text(operation_id); raw = _json(request); at = _stamp(now)
        if type(expected_revision) is not int or expected_revision < 0: _invalid('Explicit Paper checkpoint revision required')
        with self._write():
            run = self._run(run_id)
            existing = self.operation(run_id, operation_id)
            if existing:
                if existing.request_json != raw or existing.base_revision != expected_revision:
                    _conflict('Logical Paper operation request changed')
                if existing.status == 'PREPARED': self._require_process(run_id, process_generation)
            else:
                self._require_process(run_id, process_generation)
                checkpoint = self._checkpoint(run_id)
                if checkpoint['revision'] != expected_revision: _conflict('Stale Paper checkpoint revision')
                if at < checkpoint['recorded_at'] or at < run['created_at']: _invalid('Paper operation clock regressed')
                pending = self._db.execute('SELECT 1 FROM paper_process_operations o LEFT JOIN paper_process_publications p '
                    'USING(run_id,operation_id) WHERE o.run_id=? AND p.operation_id IS NULL LIMIT 1', (run_id,)).fetchone()
                if pending: _conflict('Pending Paper operation must recover/publish before a new effect')
                self._db.execute('INSERT INTO paper_process_operations VALUES (?,?,?,?,?,?)',
                    (run_id, operation_id, expected_revision, raw, _digest(raw), at))
        return self.operation(run_id, operation_id)

    @staticmethod
    def _effect_hash(run_id, operation_id, state_hash, outcome_hash):
        return _digest(_json({'run_id': run_id, 'operation_id': operation_id,
                             'state_hash': state_hash, 'outcome_hash': outcome_hash}))

    def complete(self, run_id, operation_id, state, outcome, *, now, process_generation=0):
        if not isinstance(outcome, Mapping): _invalid('Paper operation outcome must be an object')
        state_raw = _state(state); outcome_raw = _json(outcome); at = _stamp(now)
        with self._write():
            operation = self.operation(run_id, operation_id)
            if operation is None: _invalid('Paper effect lacks durable operation intent')
            if operation.status != 'PREPARED':
                if operation.state_json != state_raw or operation.outcome_json != outcome_raw:
                    _conflict('Completed Paper operation effect changed')
            else:
                self._require_process(run_id, process_generation)
                current = self._checkpoint(run_id)
                if current['revision'] != operation.base_revision: _conflict('Paper effect base revision changed')
                prepared_at = self._db.execute('SELECT prepared_at FROM paper_process_operations WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()[0]
                if at < prepared_at: _invalid('Paper effect clock predates intent')
                revision = operation.base_revision + 1
                state_hash, outcome_hash = _digest(state_raw), _digest(outcome_raw)
                self._db.execute('INSERT INTO paper_process_effects VALUES (?,?,?,?,?,?,?)',
                    (run_id, operation_id, revision, outcome_raw, outcome_hash,
                     self._effect_hash(run_id, operation_id, state_hash, outcome_hash), at))
                self._db.execute('INSERT INTO paper_process_checkpoints VALUES (?,?,?,?,?,?)',
                    (run_id, revision, operation_id, state_raw, state_hash, at))
        return self.operation(run_id, operation_id)

    def mark_published(self, run_id, operation_id, effect_hash, *, now):
        at = _stamp(now)
        with self._write():
            operation = self.operation(run_id, operation_id)
            if operation is None or operation.status == 'PREPARED' or operation.effect_hash != effect_hash:
                _conflict('Publication requires the exact applied Paper effect')
            completed = self._db.execute('SELECT completed_at FROM paper_process_effects WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()[0]
            if at < completed: _invalid('Publication clock predates Paper effect')
            self._db.execute('INSERT OR IGNORE INTO paper_process_publications VALUES (?,?,?,?)',
                             (run_id, operation_id, effect_hash, at))

    def begin_process(self, run_id, instance_id, *, expected_generation, now):
        _text(instance_id); at = _stamp(now)
        if type(expected_generation) is not int or expected_generation < 0: _invalid('Explicit process generation required')
        with self._write():
            run = self._run(run_id)
            existing = self._db.execute('SELECT generation FROM paper_process_generations WHERE run_id=? AND instance_id=?', (run_id, instance_id)).fetchone()
            if existing: return existing['generation']
            latest = self._db.execute('SELECT * FROM paper_process_generations WHERE run_id=? ORDER BY generation DESC LIMIT 1', (run_id,)).fetchone()
            generation = 0 if latest is None else latest['generation']
            if generation != expected_generation: _conflict('Stale Paper process generation')
            if at < (run['created_at'] if latest is None else latest['started_at']): _invalid('Process clock regressed')
            generation += 1
            self._db.execute('INSERT INTO paper_process_generations VALUES (?,?,?,?)', (run_id, generation, instance_id, at))
        return generation

    def _control_revision(self,run_id):
        self._run(run_id)
        checkpoint=self._checkpoint(run_id)
        pauses=self._db.execute('SELECT COUNT(*) FROM paper_entry_pause_requests WHERE run_id=?',(run_id,)).fetchone()[0]
        return checkpoint['revision']+pauses

    def control_revision(self,run_id):
        """Monotonic checkpoint + control-request revision in one read snapshot."""
        owns_read=not self._db.in_transaction
        if owns_read: self._db.execute('BEGIN')
        try: return self._control_revision(run_id)
        finally:
            if owns_read: self._db.rollback()

    def request_entry_pause(self,run_id,command_id,*,actor,expected_revision,now):
        """Deny new entries atomically, retaining the runtime's process generation.

        The owning scheduler later publishes its canonical PAUSE operation. This
        control request never cancels protection or invents an execution effect.
        """
        _text(run_id); _text(command_id); _text(actor); at=_stamp(now)
        if type(expected_revision) is not int or expected_revision<0: _invalid('Exact control revision required')
        request=_json(dict(kind='ENTRY_PAUSE',run_id=run_id,command_id=command_id,actor=actor,expected_revision=expected_revision))
        with self._write():
            existing=self._db.execute('SELECT * FROM paper_entry_pause_requests WHERE command_id=?',(command_id,)).fetchone()
            if existing:
                if existing['request_json']!=request: _conflict('Entry pause command identity changed')
                _read_json(existing['request_json'],existing['request_hash'])
                return _read_json(existing['receipt_json'],existing['receipt_hash'])
            if self._control_revision(run_id)!=expected_revision: _conflict('Stale Paper control revision')
            checkpoint=self._checkpoint(run_id)
            if at<checkpoint['recorded_at']: _invalid('Control request clock predates actual checkpoint')
            if self._db.execute('SELECT COUNT(*) FROM paper_entry_pause_requests').fetchone()[0]>=100000:
                _invalid('Entry pause audit capacity reached')
            receipt=dict(command_id=command_id,run_id=run_id,actor=actor,status='PAUSED',expected_revision=expected_revision,
                resource_revision=expected_revision+1,observed_at=at,reason_codes=['PROTECTION_MANAGEMENT_CONTINUES'])
            raw=_json(receipt)
            self._db.execute('INSERT INTO paper_entry_pause_requests VALUES(?,?,?,?,?,?,?)',
                (command_id,run_id,request,_digest(request),raw,_digest(raw),at))
            return receipt

    def entry_pause_requested(self,run_id):
        self._run(run_id)
        row=self._db.execute('SELECT request_json,request_hash FROM paper_entry_pause_requests WHERE run_id=? LIMIT 1',(run_id,)).fetchone()
        if row is None: return False
        _read_json(row['request_json'],row['request_hash'])
        return True

    def pending_entry_pauses(self,run_id,*,limit=32):
        self._run(run_id)
        if type(limit) is not int or not 1<=limit<=32: _invalid('Bounded control batch required')
        rows=self._db.execute('''SELECT p.* FROM paper_entry_pause_requests p
            LEFT JOIN paper_process_publications done ON done.run_id=p.run_id AND done.operation_id='pause:'||p.command_id
            WHERE p.run_id=? AND done.operation_id IS NULL ORDER BY p.requested_at,p.command_id LIMIT ?''',(run_id,limit)).fetchall()
        return tuple(_read_json(row['request_json'],row['request_hash']) for row in rows)

    def recover(self, run_id):
        # One read snapshot prevents mixing a checkpoint and outbox from different
        # commits while another owned connection finishes an operation.
        own_read = not self._db.in_transaction
        if own_read: self._db.execute('BEGIN')
        try:
            run = self._run(run_id); checkpoint = self._checkpoint(run_id)
            rows = self._db.execute('SELECT operation_id FROM paper_process_operations WHERE run_id=? ORDER BY base_revision,operation_id', (run_id,)).fetchall()
            pending, has_prepared = [], False
            for row in rows:
                operation = self.operation(run_id, row['operation_id'])
                if operation.status != 'PUBLISHED': pending.append(operation.operation_id)
                has_prepared = has_prepared or operation.status == 'PREPARED'
            generation = self._db.execute('SELECT COALESCE(MAX(generation),0) FROM paper_process_generations WHERE run_id=?', (run_id,)).fetchone()[0]
            status = 'PREPARED_PENDING' if has_prepared else 'PUBLICATION_PENDING' if pending else 'RECONCILIATION_REQUIRED'
            result = PaperProcessRecovery(run_id, run['binding_json'], checkpoint['revision'], checkpoint['state_json'], status, tuple(pending), generation)
        finally:
            if own_read: self._db.rollback()
        if own_read: _state(result.state)
        return result


def open_paper_process_journal(path: str | Path, *, require_existing: bool = False) -> PaperProcessJournal:
    from application.platform.resources import require_local_database_volume
    require_local_database_volume(Path(path))
    connection = _connect(path, require_existing=require_existing)
    try:
        _apply_migrations(connection)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('PRAGMA busy_timeout=5000')
        connection.isolation_level = None
        return PaperProcessJournal(connection)
    except BaseException:
        connection.close()
        raise
