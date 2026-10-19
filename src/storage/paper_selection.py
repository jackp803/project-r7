"""Protected ordinary Paper selections in the existing E6 canonical database.

Reads never initialize storage or allocate a generation. This ledger selects
configuration; it issues neither qualified releases nor workflow permission.
"""
from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from ._sqlite_registry import _connect, _MIGRATIONS_DIR
from .qualification import _canonical, _digest, _hash, _manifest, _pairs, _schema, _signatures, _require_namespace,_readonly_uri

_MIGRATION = '0019_paper_operational_selections.sql'
_TABLE = 'paper_operational_selections'
_CAPABILITY = object()


class PaperSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class OperationalSelection:
    generation: int
    config_hash: str
    canonical_json: str

    def as_dict(self):
        return json.loads(self.canonical_json)


def _record(record):
    try:
        raw = _manifest(record)
        if len(raw.encode('utf-8')) > 65536:
            raise ValueError()
        if set(record) not in ({'envelope','owner','simulator_profile'},
                {'envelope','owner','simulator_profile','source_subject'}):
            raise ValueError()
        envelope = record['envelope']
        if (not isinstance(envelope, dict) or set(envelope) != {'schema_version', 'product_config_hash',
                'owner_selection_hash', 'simulator_profile_hash', 'account_ref'} or
                envelope['schema_version'] != 'r7-paper-operational-selection-v0.2'):
            raise ValueError()
        for name in ('product_config_hash', 'owner_selection_hash', 'simulator_profile_hash'):
            _hash(envelope[name])
        for body, commitment in (('owner','owner_selection_hash'),('simulator_profile','simulator_profile_hash')):
            if _digest(_manifest(record[body])) != envelope[commitment]:
                raise ValueError()
        if (not isinstance(envelope['account_ref'], str) or not envelope['account_ref'].strip()
                or len(envelope['account_ref']) > 256):
            raise ValueError()
        return raw, _digest(_canonical(envelope))
    except (ValueError, TypeError, KeyError, RecursionError):
        raise PaperSelectionError('PAPER_OPERATIONAL_SELECTION_INVALID') from None


def _signature():
    with closing(sqlite3.connect(':memory:')) as model:
        model.executescript((_MIGRATIONS_DIR / _MIGRATION).read_text(encoding='utf-8'))
        return _schema(model, _TABLE)


class _SelectionReader:
    def __init__(self, db, signature):
        self._db, self._signature = db, signature

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _require(self):
        _require_namespace(self._db, 'LOCAL_RESEARCH', _signatures()[1])
        if (_schema(self._db, _TABLE) != self._signature or self._db.execute(
                'SELECT migration_name FROM schema_migrations WHERE migration_name=?', (_MIGRATION,)).fetchone() is None):
            raise PaperSelectionError('PAPER_SELECTION_SCHEMA_INVALID')
        count, maximum = self._db.execute('SELECT COUNT(*),MAX(generation) FROM '+_TABLE).fetchone()
        if maximum is not None and (type(maximum) is not int or not 1 <= maximum <= 2147483647 or count != maximum):
            raise PaperSelectionError('PAPER_SELECTION_GENERATION_INVALID')
        return maximum

    def _get(self, generation):
        row = self._db.execute('SELECT * FROM '+_TABLE+' WHERE generation=?', (generation,)).fetchone()
        if row is None:
            return None
        try:
            raw = row['selection_json']
            if not isinstance(raw, str) or len(raw.encode('utf-8')) > 65536:
                raise ValueError()
            parsed = json.loads(raw, object_pairs_hook=_pairs)
            canonical, config_hash = _record(parsed)
            if canonical != raw or _digest(raw) != row['selection_hash'] or config_hash != row['config_hash']:
                raise ValueError()
            return OperationalSelection(row['generation'], config_hash, raw)
        except (ValueError, TypeError, KeyError, RecursionError):
            raise PaperSelectionError('PAPER_SELECTION_RECORD_INVALID') from None

    def current(self):
        return self.get(None)

    def get(self, generation):
        if generation is not None and (type(generation) is not int or not 1 <= generation <= 2147483647):
            raise PaperSelectionError('PAPER_SELECTION_GENERATION_INVALID')
        self._db.execute('BEGIN')
        try:
            latest = self._require()
            return self._get(latest if generation is None else generation)
        finally:
            self._db.rollback()


class _SelectionOwner(_SelectionReader):
    def __init__(self, db, signature, *, capability=None):
        if capability is not _CAPABILITY:
            raise PaperSelectionError('PAPER_SELECTION_WRITER_CAPABILITY_REQUIRED')
        super().__init__(db, signature)

    def select(self, record):
        raw, config_hash = _record(record)
        self._db.execute('BEGIN IMMEDIATE')
        try:
            generation = self._require()
            previous = self._get(generation)
            if previous is not None and previous.canonical_json == raw:
                self._db.rollback()
                return previous
            if generation == 2147483647:
                raise PaperSelectionError('PAPER_SELECTION_GENERATION_EXHAUSTED')
            generation = 1 if generation is None else generation+1
            self._db.execute('INSERT INTO '+_TABLE+' VALUES(?,?,?,?)',
                (generation, config_hash, raw, _digest(raw)))
            self._db.commit()
            return OperationalSelection(generation, config_hash, raw)
        except BaseException:
            self._db.rollback()
            raise


def _open(path, *, writer,immutable=False):
    if type(immutable) is not bool or writer and immutable:raise PaperSelectionError('PAPER_SELECTION_SNAPSHOT_MODE_INVALID')
    db = None
    try:
        from application.platform.supervision import _local_path
        path = Path(path).absolute(); _local_path(path)
        db = _connect(path, require_existing=True) if writer else sqlite3.connect(_readonly_uri(path,immutable=immutable), uri=True)
        db.row_factory = sqlite3.Row; db.isolation_level = None
        db.execute('PRAGMA busy_timeout=5000')
        if writer:
            db.execute('PRAGMA synchronous=FULL')
        else:
            db.execute('PRAGMA query_only=ON')
        owner = _SelectionOwner(db, _signature(), capability=_CAPABILITY) if writer else _SelectionReader(db, _signature())
        owner._require()
        return owner
    except BaseException as error:
        if db is not None:
            db.close()
        if isinstance(error, (ValueError, OSError, sqlite3.Error)):
            raise PaperSelectionError('PAPER_SELECTION_STORE_INVALID') from error
        raise


def open_paper_selections(path,*,immutable=False):
    """Immutable mode is for an already verified sealed backup snapshot only."""
    return _open(path, writer=False,immutable=immutable)


def _open_paper_selection_owner(path):
    return _open(path, writer=True)
