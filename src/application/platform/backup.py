"""Consistent private database snapshots for supervised native local owners.

Not restoration, a data-root mirror, an upgrade or financial authorization.
SQLite backups use committed pages, never a file copy of an active DB/WAL.
"""
from contextlib import ExitStack, closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from urllib.parse import quote

from application.config import ProductConfig, load_config
from application.platform.paths import overlapping
from application.platform.private_files import create_private_directory, require_private, write_private_new, _filesystem_path
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.platform.supervision import _local_path, config_hash
from application.research.evidence import capture_provenance, stamp


class BackupError(RuntimeError):
    """Sanitized local snapshot failure; partial artifacts are never ready."""


SCHEMA = 'r7-private-sqlite-backup-v0.2'
MAX_DATABASE_BYTES = 16 * 1024**3
TOP_KEYS = {'schema_version', 'backup_id', 'created_at', 'product_instance_id', 'config_hash',
            'data_class', 'cloud_publication', 'consistency', 'source_provenance', 'databases', 'absent_databases'}
ROW_KEYS = {'logical_name', 'relative_path', 'artifact', 'sha256', 'bytes', 'schema_hash', 'user_version'}
CONSISTENCY = 'SUPERVISED_OWNERS_STOPPED_AND_DATABASE_WRITERS_FENCED'


def _inventory(config, *, include_settings=False):
    if not isinstance(config, ProductConfig):
        raise BackupError('VALIDATED_LOCAL_PROFILE_REQUIRED')
    paths = {'canonical': config.database_path}
    paths.update({name: config.local_data_root / filename for name, filename in (
        ('intake', 'intake.sqlite'), ('queue', 'queue.sqlite'), ('research', 'research.sqlite'),
        ('control', 'control-commands.sqlite'), ('auth', 'local-auth.sqlite'), ('supervision', 'process-supervision.sqlite'))})
    if include_settings:
        paths['settings'] = config.local_data_root / 'control-settings.sqlite'
    if (len(set(paths.values())) != len(paths)
            or any(not path.is_absolute() or not path.is_relative_to(config.local_data_root) or path == config.local_data_root for path in paths.values())):
        raise BackupError('DISTINCT_LOCAL_DATABASE_INVENTORY_REQUIRED')
    return dict(sorted(paths.items()))


def _destination(config, destination):
    path = Path(destination)
    if (not path.is_absolute() or '..' in path.parts or overlapping(path, config.local_data_root)
            or config.cloud_root is not None and overlapping(path, config.cloud_root)):
        raise BackupError('DISJOINT_PRIVATE_LOCAL_DESTINATION_REQUIRED')
    from application.entrypoints import _outside_installation
    _outside_installation(path)
    _local_path(path)
    return path


def _deadline(end):
    if time.monotonic() >= end:
        raise BackupError('DATABASE_BACKUP_DEADLINE_EXCEEDED')


def _connect(path, mode, end, *, immutable=False):
    _local_path(path)
    suffix = '&immutable=1' if immutable else ''
    uri = 'file:' + quote(str(_filesystem_path(path)), safe='/:') if os.name == 'nt' else path.as_uri()
    db = sqlite3.connect(uri + '?mode=' + mode + suffix, timeout=min(2, max(0.001, end - time.monotonic())), uri=True)
    db.execute('PRAGMA trusted_schema=OFF')
    db.set_progress_handler(lambda: int(time.monotonic() >= end), 1000)
    return db


def _database_facts(db):
    if db.execute('PRAGMA quick_check').fetchmany(2) != [('ok',)]:
        raise BackupError('DATABASE_INTEGRITY_FAILURE')
    if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise BackupError('DATABASE_FOREIGN_KEY_FAILURE')
    schema = db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchmany(10001)
    if len(schema) > 10000:
        raise BackupError('DATABASE_SCHEMA_LIMIT')
    raw = json.dumps(schema, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return {'schema_hash': 'sha256:' + hashlib.sha256(raw).hexdigest(), 'user_version': db.execute('PRAGMA user_version').fetchone()[0]}


def _hash_file(path, end):
    _local_path(path)
    native = _filesystem_path(path)
    size = native.stat().st_size
    if not 0 < size <= MAX_DATABASE_BYTES:
        raise BackupError('DATABASE_SIZE_LIMIT')
    digest = hashlib.sha256()
    with native.open('rb') as stream:
        while raw := stream.read(1024 * 1024):
            _deadline(end)
            digest.update(raw)
    if native.stat().st_size != size:
        raise BackupError('BACKUP_ARTIFACT_CHANGED')
    return {'sha256': 'sha256:' + digest.hexdigest(), 'bytes': size}


def _profile_current(config, config_path):
    if config_path is not None and config_hash(load_config(config_path)) != config_hash(config):
        raise BackupError('BACKUP_PROFILE_CHANGED')


def _present(inventory):
    result = set()
    for name, path in inventory.items():
        _local_path(path)
        native = _filesystem_path(path)
        if native.exists():
            if not native.is_file() or native.stat().st_nlink != 1:
                raise BackupError('REGULAR_SINGLE_LINK_DATABASE_REQUIRED')
            result.add(name)
    if 'canonical' not in result:
        raise BackupError('CANONICAL_DATABASE_REQUIRED')
    return result


def _capture_database_bundle(config, path, inventory, end, stack, *, config_path=None):
    """Caller holds all owner scopes; writer fences survive until stack exit."""
    present = _present(inventory)
    for name in sorted(present):
        _deadline(end)
        db = stack.enter_context(closing(_connect(inventory[name], 'rw', end)))
        db.execute('BEGIN IMMEDIATE')
        _database_facts(db)
    if _present(inventory) != present:
        raise BackupError('BACKUP_DATABASE_INVENTORY_CHANGED')
    create_private_directory(path)
    rows = []
    for name in sorted(present):
        _deadline(end)
        target = path / (name + '.sqlite')
        write_private_new(target, b'')
        with closing(_connect(inventory[name], 'ro', end)) as source, closing(_connect(target, 'rw', end)) as copied:
            copied.execute('PRAGMA journal_mode=DELETE')
            copied.execute('PRAGMA synchronous=FULL')
            source.backup(copied, pages=128, progress=lambda *_: _deadline(end), sleep=0.05)
            copied.execute('PRAGMA journal_mode=DELETE')
            facts = _database_facts(copied)
        require_private(target)
        rows.append(dict(logical_name=name, relative_path=inventory[name].relative_to(config.local_data_root).as_posix(),
                         artifact=target.name, **_hash_file(target, end), **facts))
    _profile_current(config, config_path)
    if _present(inventory) != present:
        raise BackupError('BACKUP_DATABASE_INVENTORY_CHANGED')
    manifest = dict(schema_version=SCHEMA, backup_id=str(uuid.uuid4()), created_at=stamp(datetime.now(timezone.utc)),
        product_instance_id=config.product_instance_id, config_hash=config_hash(config), data_class='PRIVATE_LOCAL',
        cloud_publication='FORBIDDEN', consistency=CONSISTENCY, source_provenance=capture_provenance(),
        databases=rows, absent_databases=sorted(set(inventory) - present))
    _deadline(end)
    write_private_new(path / 'manifest.json', (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    return manifest


def create_database_backup(config, destination, *, config_path=None, timeout_seconds=30):
    if type(timeout_seconds) is not int or not 5 <= timeout_seconds <= 300:
        raise BackupError('BOUNDED_DATABASE_BACKUP_DEADLINE_REQUIRED')
    end = time.monotonic() + timeout_seconds
    try:
        inventory = _inventory(config)
        path = _destination(config, destination)
        _profile_current(config, config_path)
        with ExitStack() as stack:
            for role in ('control', 'research', 'runtime', 'cloud'):
                stack.enter_context(ProcessScopeLock(role + ':' + config.product_instance_id,
                                                     lock_root=operational_lock_root(config)))
            _capture_database_bundle(config, path, inventory, end, stack, config_path=config_path)
        return verify_database_backup(config, path)
    except BackupError:
        raise
    except Exception:
        raise BackupError('LOCAL_DATABASE_BACKUP_FAILED') from None


def _unique_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise BackupError('BACKUP_MANIFEST_DUPLICATE_KEY')
        result[name] = value
    return result


def verify_database_backup(config, destination, *, timeout_seconds=30, _include_settings=False):
    return _verify_database_backup_snapshot(config,destination,timeout_seconds=timeout_seconds,
        _include_settings=_include_settings)[0]


def _verify_database_backup_snapshot(config, destination, *, timeout_seconds=30, _include_settings=False):
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=300:
        raise BackupError('BOUNDED_DATABASE_VERIFICATION_DEADLINE_REQUIRED')
    end = time.monotonic() + timeout_seconds
    try:
        inventory = _inventory(config, include_settings=_include_settings)
        path = _destination(config, destination)
        require_private(path, directory=True)
        manifest_path = path / 'manifest.json'
        require_private(manifest_path)
        with _filesystem_path(manifest_path).open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise BackupError('BACKUP_MANIFEST_SIZE_LIMIT')
        manifest = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_pairs,
                              parse_constant=lambda _: (_ for _ in ()).throw(BackupError('BACKUP_MANIFEST_INVALID')))
        if (not isinstance(manifest, dict) or set(manifest) != TOP_KEYS or manifest['schema_version'] != SCHEMA
                or manifest['data_class'] != 'PRIVATE_LOCAL' or manifest['cloud_publication'] != 'FORBIDDEN'
                or manifest['consistency'] != CONSISTENCY or manifest['product_instance_id'] != config.product_instance_id
                or manifest['config_hash'] != config_hash(config) or not isinstance(manifest['source_provenance'], dict)):
            raise BackupError('BACKUP_MANIFEST_INVALID')
        if str(uuid.UUID(manifest['backup_id'])) != manifest['backup_id']:
            raise BackupError('BACKUP_MANIFEST_INVALID')
        stamp(datetime.fromisoformat(manifest['created_at'].replace('Z', '+00:00')))
        rows, absent = manifest['databases'], manifest['absent_databases']
        if (not isinstance(rows, list) or not 1 <= len(rows) <= len(inventory) or not isinstance(absent, list)
                or any(not isinstance(value, str) for value in absent) or len(absent) != len(set(absent))):
            raise BackupError('BACKUP_MANIFEST_INVALID')
        found = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != ROW_KEYS:
                raise BackupError('BACKUP_MANIFEST_INVALID')
            name = row['logical_name']
            if (not isinstance(name, str) or name not in inventory or name in found
                    or row['artifact'] != name + '.sqlite'
                    or row['relative_path'] != inventory[name].relative_to(config.local_data_root).as_posix()
                    or type(row['bytes']) is not int or not 0 < row['bytes'] <= MAX_DATABASE_BYTES
                    or type(row['user_version']) is not int or not 0 <= row['user_version'] < 2**31
                    or any(not isinstance(row[key], str) or not re.fullmatch('sha256:[0-9a-f]{64}', row[key]) for key in ('sha256', 'schema_hash'))):
                raise BackupError('BACKUP_MANIFEST_INVALID')
            found.add(name)
            target = path / row['artifact']
            require_private(target)
            if _hash_file(target, end) != {key: row[key] for key in ('sha256', 'bytes')}:
                raise BackupError('BACKUP_ARTIFACT_HASH_MISMATCH')
            # Sealed artifacts only: immutable prevents SQLite from creating
            # WAL/SHM files while inspecting a retained WAL-mode header. Never
            # use immutable for the actively written source database.
            with closing(_connect(target, 'ro', end, immutable=True)) as db:
                if _database_facts(db) != {key: row[key] for key in ('schema_hash', 'user_version')}:
                    raise BackupError('BACKUP_DATABASE_SCHEMA_MISMATCH')
            require_private(target)
            if _hash_file(target, end) != {key: row[key] for key in ('sha256', 'bytes')}:
                raise BackupError('BACKUP_ARTIFACT_CHANGED_DURING_INSPECTION')
        if 'canonical' not in found or found & set(absent) or found | set(absent) != set(inventory):
            raise BackupError('BACKUP_MANIFEST_INVENTORY_INVALID')
        if {item.name for item in _filesystem_path(path).iterdir()} != {'manifest.json', *(name + '.sqlite' for name in found)}:
            raise BackupError('BACKUP_UNEXPECTED_ARTIFACT')
        with _filesystem_path(manifest_path).open('rb') as stream:
            if stream.read(65537)!=raw:
                raise BackupError('BACKUP_MANIFEST_CHANGED_DURING_INSPECTION')
        summary=dict(status='DATABASE_BACKUP_VERIFIED', schema_version=SCHEMA, backup_id=manifest['backup_id'],
                    database_count=len(rows), data_class='PRIVATE_LOCAL', cloud_publication='FORBIDDEN',
                    financial_authority='NONE', restore='NOT_PERFORMED')
        return summary,manifest,raw
    except BackupError:
        raise
    except Exception:
        raise BackupError('LOCAL_DATABASE_BACKUP_VERIFICATION_FAILED') from None
