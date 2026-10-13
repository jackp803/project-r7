"""Ordinary selection generations in the existing canonical store, without grants."""
import importlib
import importlib.util
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier

from storage import open_sqlite_platform


class PaperOperationalSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r7-paper-selection-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'canonical.sqlite3'
        with open_sqlite_platform(self.path, research_namespace='LOCAL_RESEARCH'):
            pass

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('storage.paper_selection'),
            'Ordinary selection must use a protected durable generation, not fixture generation 1')
        return importlib.import_module('storage.paper_selection')

    def record(self, account='explicit-test-account'):
        from application.config import ProductConfig
        from application.paper.release import operational_record
        from tests.application.test_paper_release_selection import PaperReleaseSelectionTests
        config=ProductConfig('r7-product-config-v0.2','selection-ledger-test',self.path.parent,None,self.path,
            diagnostic_only=False,paper_runtime_enabled=True)
        return operational_record(config,PaperReleaseSelectionTests().owner(),account_ref=account)

    def test_body_mutation_or_missing_owner_is_rejected_without_allocating_generation(self):
        m=self.module()
        with m._open_paper_selection_owner(self.path) as owner:
            for field in ('owner','simulator_profile'):
                record=self.record();record[field]['forged']=True
                with self.subTest(field=field),self.assertRaises(m.PaperSelectionError):owner.select(record)
                record=self.record();del record[field]
                with self.assertRaises(m.PaperSelectionError):owner.select(record)
            self.assertIsNone(owner.current())

    def test_missing_selection_read_does_not_allocate_generation_or_create_database(self):
        m = self.module()
        with m.open_paper_selections(self.path) as reader:
            self.assertIsNone(reader.current())
            self.assertFalse(hasattr(reader, 'select'))
        absent = self.path.with_name('absent.sqlite3')
        with self.assertRaises(m.PaperSelectionError):
            m.open_paper_selections(absent)
        self.assertFalse(absent.exists())

    def test_identical_selection_is_idempotent_across_restart_and_read_only_reads(self):
        m = self.module(); record = self.record()
        with m._open_paper_selection_owner(self.path) as owner:
            first = owner.select(record)
            self.assertEqual(first.generation, 1)
        record['envelope']['account_ref'] = 'changed-after-append'
        with m._open_paper_selection_owner(self.path) as owner:
            self.assertEqual(owner.select(self.record()), first)
        with m.open_paper_selections(self.path) as reader:
            for _ in range(3):
                self.assertEqual(reader.current(), first)
            view = first.as_dict(); view['envelope']['account_ref'] = 'view-mutation'
            self.assertEqual(first.as_dict()['envelope']['account_ref'], 'explicit-test-account')
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM paper_operational_selections').fetchone()[0], 1)

    def test_material_change_increments_and_keeps_original_selection_immutable(self):
        m = self.module()
        with m._open_paper_selection_owner(self.path) as owner:
            first = owner.select(self.record())
            second = owner.select(self.record('different-explicit-account'))
            self.assertEqual(second.generation, 2)
            self.assertNotEqual(first.config_hash, second.config_hash)
        with m.open_paper_selections(self.path) as reader:
            self.assertEqual(reader.get(1), first)
            self.assertEqual(reader.current(), second)
        with closing(sqlite3.connect(self.path)) as db:
            for sql in ('DELETE FROM paper_operational_selections',
                        'UPDATE paper_operational_selections SET generation=3'):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)

    def test_concurrent_identical_selection_allocates_one_generation(self):
        m = self.module(); barrier = Barrier(2)
        def select():
            barrier.wait(timeout=5)
            with m._open_paper_selection_owner(self.path) as owner:
                return owner.select(self.record())
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: select(), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0].generation, 1)

    def test_fixture_namespace_and_corrupt_history_fail_closed(self):
        m = self.module()
        fixture = self.path.with_name('fixture.sqlite3')
        with open_sqlite_platform(fixture, research_namespace='FIXTURE'):
            pass
        for factory in (m.open_paper_selections, m._open_paper_selection_owner):
            with self.assertRaises(m.PaperSelectionError):
                factory(fixture)
        with m._open_paper_selection_owner(self.path) as owner:
            owner.select(self.record())
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TRIGGER paper_operational_selections_no_update')
            db.execute('UPDATE paper_operational_selections SET generation=2147483647')
        for factory in (m.open_paper_selections, m._open_paper_selection_owner):
            with self.assertRaises(m.PaperSelectionError):
                with factory(self.path) as owner:
                    owner.current()


if __name__ == '__main__':
    unittest.main()
