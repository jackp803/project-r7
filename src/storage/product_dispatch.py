"""E6 durable provider intents/dispatch claims, without financial or I/O authority.

The first claim commits before I/O; every later claimant must read back. A stored
claim, approval hash, generation or observation cannot grant another POST.
Canonical domain publication remains with the existing E6 runtime journal.
"""
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json, re, sqlite3

from registry.operational_authority import CurrentRuntimePermission
from registry.product_assessment import canonical, digest
from storage._sqlite_registry import _connect, _apply_migrations
from brokers.okx_production_transport import _body


class ProductDispatchError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _text(value):
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 256 or any(c in value for c in '\x00\r\n'):
        raise ProductDispatchError('DISPATCH_BOUNDED_IDENTITY_REQUIRED')
    return value


def _stamp(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ProductDispatchError('DISPATCH_UTC_REQUIRED')
    return value.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _json(value):
    stack, count = [(value, 0)], 0
    while stack:
        node, depth = stack.pop(); count += 1
        if depth > 24 or count > 20000:
            raise ProductDispatchError('DISPATCH_PAYLOAD_COMPLEXITY_LIMIT')
        if isinstance(node, dict):
            for key, child in node.items():
                _text(key)
                if any(part in key.casefold() for part in ('authorization', 'cookie', 'password', 'credential', 'secret', 'passphrase', 'api_key', 'token', 'private_key', 'raw_payload')):
                    raise ProductDispatchError('DISPATCH_PRIVATE_PAYLOAD_FORBIDDEN')
                stack.append((child, depth + 1))
        elif isinstance(node, list):
            stack.extend((child, depth + 1) for child in node)
        elif isinstance(node, str):
            if len(node) > 4096 or '\x00' in node:
                raise ProductDispatchError('DISPATCH_TEXT_LIMIT')
        elif node is None or type(node) is bool:
            pass
        elif type(node) is int and abs(node) < 2**63:
            pass
        else:
            raise ProductDispatchError('DISPATCH_PURE_JSON_REQUIRED')
    return canonical(value)


def _read(raw, expected):
    if digest(raw) != expected:
        raise ProductDispatchError('DISPATCH_STORED_HASH_MISMATCH')
    try:
        value = json.loads(raw)
    except (ValueError, RecursionError):
        raise ProductDispatchError('DISPATCH_STORED_JSON_INVALID') from None
    if _json(value) != raw:
        raise ProductDispatchError('DISPATCH_STORED_JSON_NONCANONICAL')
    return value


@dataclass(frozen=True)
class ProductProcessLease:
    run_id: str
    generation: int
    instance_id: str


@dataclass(frozen=True)
class ProductDispatchOperation:
    run_id: str
    operation_id: str
    request_json: str
    status: str
    recovery_disposition: str
    observation_json: str | None

    @property
    def request(self):
        return json.loads(self.request_json)


@dataclass(frozen=True)
class ProductDispatchRecovery:
    run_id: str
    ambiguous_operations: tuple[str, ...]
    prepared_operations: tuple[str, ...]
    process_generation: int


class ProductDispatchJournal:
    def __init__(self, connection):
        self._db = connection
        self._closed = False

    def close(self):
        if not self._closed:
            self._db.close(); self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def _write(self):
        try:
            if self._db.in_transaction:
                raise ProductDispatchError('DISPATCH_IDLE_WRITER_REQUIRED')
            self._db.execute('BEGIN IMMEDIATE')
            yield
            self._db.commit()
        except sqlite3.Error:
            if not self._closed: self._db.rollback()
            raise ProductDispatchError('DISPATCH_DURABLE_WRITE_FAILED') from None
        except BaseException:
            if not self._closed: self._db.rollback()
            raise

    def ensure_run(self, run_id, permission, *, now):
        _text(run_id); at = _stamp(now)
        if (type(permission) is not CurrentRuntimePermission or permission.namespace != permission.release.namespace or
            (permission.namespace, permission.execution) not in {('FIXTURE', 'SIMULATED_MECHANICS'), ('LOCAL_RESEARCH', 'ACTUAL_OWNER')}):
            raise ProductDispatchError('DISPATCH_EXACT_OWNER_BINDING_REQUIRED')
        binding = asdict(permission)
        for field in ('permission', 'observed_at', 'registry_revision'):
            binding.pop(field)
        raw = _json(binding)
        with self._write():
            namespace = self._db.execute('SELECT namespace FROM product_dispatch_namespace WHERE singleton=1').fetchone()
            if namespace is None:
                self._db.execute('INSERT INTO product_dispatch_namespace VALUES(1,?)', (permission.namespace,))
            elif namespace['namespace'] != permission.namespace:
                raise ProductDispatchError('DISPATCH_NAMESPACE_MISMATCH')
            row = self._db.execute('SELECT * FROM product_dispatch_runs WHERE run_id=?', (run_id,)).fetchone()
            if row is not None:
                _read(row['binding_json'], row['binding_hash'])
                if row['binding_json'] != raw:
                    raise ProductDispatchError('DISPATCH_RUN_BINDING_CONFLICT')
            else:
                self._db.execute('INSERT INTO product_dispatch_runs VALUES(?,?,?,?,?,?)',
                    (run_id, raw, digest(raw), permission.release.provider_ref, permission.release.account_ref, at))

    def _run(self, run_id):
        row = self._db.execute('SELECT * FROM product_dispatch_runs WHERE run_id=?', (_text(run_id),)).fetchone()
        if row is None:
            raise ProductDispatchError('DISPATCH_RUN_UNKNOWN')
        _read(row['binding_json'], row['binding_hash'])
        return row

    def _latest_process(self, run_id):
        return self._db.execute('SELECT * FROM product_dispatch_generations WHERE run_id=? ORDER BY generation DESC LIMIT 1', (run_id,)).fetchone()

    def _require_lease(self, run_id, lease, at):
        latest = self._latest_process(run_id)
        if (type(lease) is not ProductProcessLease or lease.run_id != run_id or latest is None or
            (lease.generation, lease.instance_id) != (latest['generation'], latest['instance_id']) or at < latest['started_at']):
            raise ProductDispatchError('DISPATCH_CURRENT_PROCESS_GENERATION_REQUIRED')

    def begin_process(self, run_id, instance_id, *, expected_generation, now):
        at = _stamp(now); _text(instance_id)
        if type(expected_generation) is not int or expected_generation < 0:
            raise ProductDispatchError('DISPATCH_EXPECTED_GENERATION_REQUIRED')
        with self._write():
            run = self._run(run_id); latest = self._latest_process(run_id)
            generation = 0 if latest is None else latest['generation']
            existing = self._db.execute('SELECT generation FROM product_dispatch_generations WHERE run_id=? AND instance_id=?', (run_id, instance_id)).fetchone()
            if existing is not None:
                if existing['generation'] != generation:
                    raise ProductDispatchError('DISPATCH_OLD_PROCESS_CANNOT_RESUME')
                return ProductProcessLease(run_id, generation, instance_id)
            if expected_generation != generation or at < (run['created_at'] if latest is None else latest['started_at']):
                raise ProductDispatchError('DISPATCH_PROCESS_GENERATION_CONFLICT')
            generation += 1
            self._db.execute('INSERT INTO product_dispatch_generations VALUES(?,?,?,?)', (run_id, generation, instance_id, at))
        return ProductProcessLease(run_id, generation, instance_id)

    def prepare(self, run_id, operation_id, request, *, lease, now):
        at = _stamp(now); _text(operation_id)
        required = {'role', 'path', 'native_client_id', 'body', 'canonical_request_hash', 'authority_hash'}
        if (not isinstance(request, dict) or set(request) != required or not isinstance(request['body'], dict) or
            not isinstance(request['role'], str) or request['role'] not in {'ENTRY', 'PROTECTION_STOP', 'POSITION_EXIT', 'EMERGENCY_EXIT'}):
            raise ProductDispatchError('DISPATCH_EXACT_INTENT_REQUIRED')
        path = '/api/v5/trade/order-algo' if request['role'] == 'PROTECTION_STOP' else '/api/v5/trade/order'
        body_id = 'algoClOrdId' if request['role'] == 'PROTECTION_STOP' else 'clOrdId'
        if request['path'] != path or request['body'].get(body_id) != request['native_client_id']:
            raise ProductDispatchError('DISPATCH_NATIVE_IDENTITY_MISMATCH')
        _body(path, request['body'])
        if request['role'] != 'ENTRY' and request['body'].get('reduceOnly') is not True:
            raise ProductDispatchError('DISPATCH_REDUCE_ONLY_REQUIRED')
        for field in ('canonical_request_hash', 'authority_hash'):
            if not isinstance(request[field], str) or not re.fullmatch('sha256:[0-9a-f]{64}', request[field]):
                raise ProductDispatchError('DISPATCH_EXACT_HASH_REQUIRED')
        raw = _json(request)
        with self._write():
            run = self._run(run_id); self._require_lease(run_id, lease, at)
            row = self._db.execute('SELECT * FROM product_dispatch_intents WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()
            if row is not None:
                if _read(row['request_json'], row['request_hash']) != request:
                    raise ProductDispatchError('DISPATCH_INTENT_CONFLICT')
            else:
                self._db.execute('INSERT INTO product_dispatch_intents VALUES(?,?,?,?,?,?,?,?)',
                    (run_id, operation_id, raw, digest(raw), run['provider_ref'], run['account_ref'], request['native_client_id'], at))
        return self.operation(run_id, operation_id)

    def operation(self, run_id, operation_id):
        self._run(run_id)
        row = self._db.execute('SELECT * FROM product_dispatch_intents WHERE run_id=? AND operation_id=?', (run_id, _text(operation_id))).fetchone()
        if row is None:
            return None
        _read(row['request_json'], row['request_hash'])
        claim = self._db.execute('SELECT * FROM product_dispatch_claims WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()
        observation = self._db.execute('SELECT * FROM product_dispatch_observations WHERE run_id=? AND operation_id=? ORDER BY observed_at DESC LIMIT 1', (run_id, operation_id)).fetchone()
        if observation is not None:
            _read(observation['observation_json'], observation['observation_hash'])
        return ProductDispatchOperation(run_id, operation_id, row['request_json'],
            'OBSERVED' if observation is not None else 'DISPATCHING' if claim is not None else 'PREPARED',
            'READBACK_REQUIRED' if claim is not None else 'CURRENT_ADMISSION_REQUIRED',
            None if observation is None else observation['observation_json'])

    def claim_dispatch(self, run_id, operation_id, *, lease, now):
        at = _stamp(now)
        with self._write():
            self._run(run_id); self._require_lease(run_id, lease, at)
            operation = self.operation(run_id, operation_id)
            if operation is None:
                raise ProductDispatchError('DISPATCH_INTENT_REQUIRED')
            if operation.status != 'PREPARED':
                return False
            prepared_at = self._db.execute('SELECT prepared_at FROM product_dispatch_intents WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()[0]
            if at < prepared_at:
                raise ProductDispatchError('DISPATCH_CLOCK_REGRESSED')
            self._db.execute('INSERT INTO product_dispatch_claims VALUES(?,?,?,?)', (run_id, operation_id, lease.generation, at))
        return True

    def observe(self, run_id, operation_id, observation, *, lease, now):
        at = _stamp(now)
        if (not isinstance(observation, dict) or set(observation) != {'status', 'provider_id', 'reason_code'} or
            not isinstance(observation['status'], str) or observation['status'] not in {'ACK_PENDING', 'ACK_REJECTED', 'RECONCILIATION_REQUIRED', 'ORDER_OBSERVED', 'ALGO_OBSERVED'} or
            (observation['provider_id'] is not None and (not isinstance(observation['provider_id'], str) or not re.fullmatch('[0-9]{1,64}', observation['provider_id']))) or
            not isinstance(observation['reason_code'], str) or not re.fullmatch('[A-Z0-9_]{1,128}', observation['reason_code'])):
            raise ProductDispatchError('DISPATCH_SANITIZED_OBSERVATION_REQUIRED')
        raw = _json(observation)
        with self._write():
            self._run(run_id); self._require_lease(run_id, lease, at)
            claim = self._db.execute('SELECT * FROM product_dispatch_claims WHERE run_id=? AND operation_id=?', (run_id, operation_id)).fetchone()
            if claim is None or at < claim['dispatched_at']:
                raise ProductDispatchError('DISPATCH_OBSERVATION_WITHOUT_PRIOR_CLAIM')
            existing = self._db.execute('SELECT * FROM product_dispatch_observations WHERE run_id=? AND operation_id=? AND observed_at=?', (run_id, operation_id, at)).fetchone()
            if existing is not None:
                if existing['observation_json'] != raw or existing['observation_hash'] != digest(raw):
                    raise ProductDispatchError('DISPATCH_EQUAL_TIME_OBSERVATION_CONFLICT')
            else:
                self._db.execute('INSERT INTO product_dispatch_observations VALUES(?,?,?,?,?,?)', (run_id, operation_id, at, raw, digest(raw), lease.generation))

    def recover(self, run_id):
        self._run(run_id)
        operations = [self.operation(run_id, row[0]) for row in self._db.execute('SELECT operation_id FROM product_dispatch_intents WHERE run_id=? ORDER BY prepared_at,operation_id', (run_id,))]
        latest = self._latest_process(run_id)
        return ProductDispatchRecovery(run_id,
            tuple(operation.operation_id for operation in operations if operation.status != 'PREPARED'),
            tuple(operation.operation_id for operation in operations if operation.status == 'PREPARED'),
            0 if latest is None else latest['generation'])


def open_product_dispatch_journal(path):
    connection = _connect(path)
    try:
        _apply_migrations(connection)
        connection.execute('PRAGMA synchronous=FULL')
        if connection.execute('PRAGMA synchronous').fetchone()[0] != 2:
            raise ProductDispatchError('DISPATCH_FULL_DURABILITY_REQUIRED')
        return ProductDispatchJournal(connection)
    except BaseException:
        connection.close()
        raise
