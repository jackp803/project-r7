"""Existing-only canonical journal opening; missing files never become new state."""
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from storage.paper_process import open_paper_process_journal


class PaperProcessExistingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 existing owner ')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / '既存 #100% store.sqlite'

    def test_existing_open_preserves_sqlite_owner_semantics_and_escaped_unicode_path(self):
        with open_paper_process_journal(self.path) as initialized:
            names = tuple(row[0] for row in initialized._db.execute('SELECT migration_name FROM schema_migrations ORDER BY migration_name'))
        with open_paper_process_journal(self.path, require_existing=True) as existing:
            self.assertIs(existing._db.row_factory, sqlite3.Row)
            self.assertEqual(existing._db.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            self.assertEqual(existing._db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
            self.assertEqual(existing._db.execute('PRAGMA synchronous').fetchone()[0], 2)
            self.assertEqual(existing._db.execute('PRAGMA busy_timeout').fetchone()[0], 5000)
            self.assertEqual(tuple(row[0] for row in existing._db.execute(
                'SELECT migration_name FROM schema_migrations ORDER BY migration_name')), names)
        self.assertEqual([path.name for path in self.path.parent.glob('*.sqlite')], [self.path.name])

    def test_missing_existing_open_never_initializes_canonical_store(self):
        with self.assertRaises(sqlite3.OperationalError):
            open_paper_process_journal(self.path, require_existing=True)
        self.assertFalse(self.path.exists())

    def test_existing_requirement_rejects_non_boolean_without_creating_store(self):
        for value in (0, 1, 'yes', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                open_paper_process_journal(self.path, require_existing=value)
            self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
