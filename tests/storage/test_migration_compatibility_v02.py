"""Actual writer refuses incompatible ledgers before schema/data writes."""
from contextlib import closing
from pathlib import Path
import hashlib
import sqlite3
import tempfile
import unittest

from registry.models import EvidenceGateError
from storage._sqlite_registry import _apply_migrations, _connect, _open_authorized_store


class MigrationCompatibilityV02Tests(unittest.TestCase):
    def test_actual_writer_rejects_unknown_gapped_and_unversioned_populated_databases_unchanged(self):
        for vector in ('unknown', 'gapped', 'unversioned'):
            with self.subTest(vector=vector), tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'owned-test.sqlite'
                with closing(_connect(path)) as db:
                    if vector == 'unversioned':
                        db.execute('CREATE TABLE unrelated_application_data(value TEXT)')
                        db.execute('INSERT INTO unrelated_application_data VALUES (?)',('preserve-me',))
                    else:
                        _apply_migrations(db)
                        if vector == 'unknown':
                            db.execute('INSERT INTO schema_migrations(migration_name) VALUES (?)',
                                ('9999_unknown_future_release.sql',))
                        else:
                            names = [row[0] for row in db.execute('SELECT migration_name FROM schema_migrations ORDER BY migration_name')]
                            self.assertGreater(len(names),2)
                            db.execute('DELETE FROM schema_migrations WHERE migration_name=?',(names[1],))
                    db.commit()
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                inventory = sorted(p.name for p in Path(folder).iterdir())
                with self.assertRaisesRegex(EvidenceGateError,'MIGRATION_COMPATIBILITY'):
                    store = _open_authorized_store(path,require_existing=True)
                    store.close()
                self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(inventory,sorted(p.name for p in Path(folder).iterdir()))

    def test_shared_check_is_read_only_for_fresh_prefix_and_complete_packaged_ledger(self):
        import shutil
        from storage._sqlite_registry import check_migration_compatibility, _MIGRATIONS_DIR
        known = tuple(sorted(p.name for p in _MIGRATIONS_DIR.glob('*.sql')))
        self.assertGreater(len(known),1)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'actual-prefix.sqlite'
            with closing(_connect(path)) as db:
                before = path.read_bytes()
                self.assertEqual(check_migration_compatibility(db),dict(
                    applied=(),pending=known,fresh=True,ledger_present=False))
                self.assertEqual(path.read_bytes(),before)
                self.assertEqual(db.execute("SELECT name FROM sqlite_schema").fetchall(),[])
                self.assertFalse(db.in_transaction)
                prefix = Path(folder)/'first-only'; prefix.mkdir()
                shutil.copyfile(_MIGRATIONS_DIR/known[0],prefix/known[0])
                _apply_migrations(db,prefix)
                db.execute('PRAGMA query_only=ON')
                before = path.read_bytes()
                self.assertEqual(check_migration_compatibility(db),dict(
                    applied=known[:1],pending=known[1:],fresh=False,ledger_present=True))
                self.assertEqual(path.read_bytes(),before)
                self.assertFalse(db.in_transaction)
                db.execute('PRAGMA query_only=OFF')
                _apply_migrations(db)
                before = path.read_bytes()
                self.assertEqual(check_migration_compatibility(db),dict(
                    applied=known,pending=(),fresh=False,ledger_present=True))
                _apply_migrations(db)
                self.assertEqual(path.read_bytes(),before)
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_shared_reader_accepts_normal_readonly_uri_without_running_migrations(self):
        from storage._sqlite_registry import check_migration_compatibility, _MIGRATIONS_DIR
        known = tuple(sorted(p.name for p in _MIGRATIONS_DIR.glob('*.sql')))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'readonly.sqlite'
            with closing(_connect(path)) as db: _apply_migrations(db)
            before = path.read_bytes()
            inventory = sorted(p.name for p in Path(folder).iterdir())
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
                db.execute('PRAGMA query_only=ON')
                self.assertEqual(check_migration_compatibility(db),dict(
                    applied=known,pending=(),fresh=False,ledger_present=True))
                self.assertFalse(db.in_transaction)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()),inventory)

    def test_malformed_duplicate_and_empty_populated_ledgers_are_refused_unchanged(self):
        from storage._sqlite_registry import check_migration_compatibility, _MIGRATIONS_DIR
        first = sorted(_MIGRATIONS_DIR.glob('*.sql'))[0].name
        vectors = {
            'view': ["CREATE VIEW schema_migrations AS SELECT 'bad' AS migration_name, 'bad' AS applied_at"],
            'missing-column': ['CREATE TABLE schema_migrations(migration_name TEXT PRIMARY KEY)'],
            'duplicate': ['CREATE TABLE schema_migrations(migration_name TEXT, applied_at TEXT NOT NULL)',
                "INSERT INTO schema_migrations VALUES (?, 'fixture')", "INSERT INTO schema_migrations VALUES (?, 'fixture')"],
            'null-name': ['CREATE TABLE schema_migrations(migration_name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)',
                "INSERT INTO schema_migrations VALUES(NULL,'fixture')"],
            'extra-column': ['CREATE TABLE schema_migrations(migration_name TEXT PRIMARY KEY, applied_at TEXT NOT NULL, extra TEXT)'],
            'generated-column': ['CREATE TABLE schema_migrations(migration_name TEXT PRIMARY KEY, applied_at TEXT NOT NULL, extra TEXT GENERATED ALWAYS AS (migration_name) VIRTUAL)'],
            'empty-populated': ['CREATE TABLE schema_migrations(migration_name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)',
                'CREATE TABLE preserved(value TEXT)', "INSERT INTO preserved VALUES('keep')"],
            # GLOB must treat the underscore literally; sqliteX is NOT SQLite-internal.
            'unversioned-sqliteX': ['CREATE TABLE sqliteX_user_data(value TEXT)'],
        }
        for vector,statements in vectors.items():
            with self.subTest(vector=vector), tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'malformed.sqlite'
                with closing(_connect(path)) as db:
                    for statement in statements:
                        db.execute(statement,(first,)) if '?' in statement else db.execute(statement)
                    db.commit()
                before=path.read_bytes(); inventory=sorted(p.name for p in Path(folder).iterdir())
                with closing(_connect(path)) as db:
                    with self.assertRaisesRegex(EvidenceGateError,'MIGRATION_COMPATIBILITY'):
                        check_migration_compatibility(db)
                    self.assertFalse(db.in_transaction)
                with self.assertRaisesRegex(EvidenceGateError,'MIGRATION_COMPATIBILITY'):
                    store=_open_authorized_store(path,require_existing=True)
                    store.close()
                self.assertEqual(path.read_bytes(),before)
                self.assertEqual(sorted(p.name for p in Path(folder).iterdir()),inventory)
