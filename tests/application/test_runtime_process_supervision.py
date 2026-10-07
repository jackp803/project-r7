from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
import unittest
from unittest import mock

from application.config import ProductConfig
from application.platform.scope_lock import ScopeBusy


class RuntimeProcessSupervisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 runtime supervision ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = ProductConfig('r7-product-config-v0.2', self.root.name.replace(' ', '-'),
            self.root / '資料', None, self.root / '資料/canonical.sqlite3')
        self.profile = self.root / '設定.json'
        self.write_profile()
        self.module = importlib.import_module('application.platform.supervision')

    def write_profile(self, **changes):
        values = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(self.config).items()}
        values.update(changes)
        self.profile.write_text(json.dumps(values, ensure_ascii=False), encoding='utf-8')

    def session(self, role, **options):
        return self.module.ProcessSupervisor(self.config, role, config_path=self.profile,
            heartbeat_interval=0.05, **options)

    def wait_heartbeat(self, owner, previous):
        deadline = time.monotonic() + 2
        while owner.health()['heartbeat_sequence'] <= previous:
            if time.monotonic() >= deadline:
                self.fail('Actual supervisor heartbeat did not advance')
            time.sleep(0.02)
        owner.require_current()

    def test_runtime_and_cloud_are_independent_actual_owner_generations_without_permission(self):
        with self.session('runtime') as runtime, self.session('cloud') as cloud:
            for owner in (runtime, cloud):
                self.assertEqual(owner.identity['generation'], 1)
                self.assertEqual(owner.identity['financial_authority'], 'NONE')
                self.assertEqual(owner.identity['restart_admission'], 'RECONCILIATION_REQUIRED')
                self.assertEqual(owner.health()['status'], 'RECENT_HEARTBEAT')
                owner.require_current()
            self.assertNotEqual(runtime.identity['process_generation_id'], cloud.identity['process_generation_id'])
        with self.session('runtime') as next_runtime, self.session('cloud') as next_cloud:
            self.assertEqual(next_runtime.identity['generation'], 2)
            self.assertEqual(next_cloud.identity['generation'], 2)
            self.assertNotEqual(next_runtime.identity['process_generation_id'], runtime.identity['process_generation_id'])

    def test_duplicate_runtime_owner_is_denied_without_replacing_generation(self):
        with self.session('runtime') as first:
            token = first.identity['process_generation_id']
            with self.assertRaises(ScopeBusy):
                with self.session('runtime'):
                    self.fail('Second owner acquired the same role scope')
            self.assertEqual(first.health()['process_generation_id'], token)
            first.require_current()

    def test_runtime_heartbeat_advances_while_other_owner_is_present(self):
        with self.session('runtime') as runtime, self.session('research') as research:
            self.wait_heartbeat(runtime, runtime.health()['heartbeat_sequence'])
            research.require_current()

    def test_cloud_configuration_drift_inhibits_without_renewing_owner(self):
        with self.session('cloud') as cloud:
            token = cloud.identity['process_generation_id']
            self.write_profile(scan_interval=31)
            deadline = time.monotonic() + 2
            while not cloud.failed:
                if time.monotonic() >= deadline:
                    self.fail('Configuration drift did not inhibit the actual cloud generation')
                time.sleep(0.02)
            self.assertEqual(cloud.health()['status'], 'CONFIG_CHANGED')
            self.assertEqual(cloud.identity['process_generation_id'], token)
            with self.assertRaises(self.module.SupervisionError):
                cloud.require_current()

    def test_stolen_runtime_generation_is_fenced_without_stopping_cloud(self):
        with self.session('cloud') as cloud:
            with self.assertRaises(self.module.SupervisionError):
                with self.session('runtime') as runtime:
                    with closing(sqlite3.connect(runtime.path)) as db, db:
                        db.execute("UPDATE process_sessions SET process_generation_id='fixture-successor' WHERE role='runtime'")
                    runtime.require_current()
            cloud.require_current()

    def test_new_roles_read_only_health_does_not_create_database(self):
        for role in ('runtime', 'cloud'):
            self.assertEqual(self.module.process_health(self.config, role),
                dict(status='NOT_STARTED', financial_authority='NONE'))
        self.assertFalse((self.config.local_data_root / 'process-supervision.sqlite').exists())

    def test_unknown_role_is_denied_without_creating_database(self):
        with self.assertRaises(ValueError):
            self.session('unapproved')
        with self.assertRaises(ValueError):
            self.module.process_health(self.config, 'unapproved')
        self.assertFalse((self.config.local_data_root / 'process-supervision.sqlite').exists())

    def legacy_database(self, factory=sqlite3.Connection):
        db = sqlite3.connect(self.root / 'legacy.sqlite', factory=factory)
        self.addCleanup(db.close)
        migration = Path(self.module.__file__).parents[1] / 'migrations/0006_process_supervision.sql'
        db.executescript(migration.read_text(encoding='utf-8'))
        started = '2026-10-07T00:00:00.000000Z'
        for role, generation in (('control',7), ('research',9)):
            token = 'legacy-' + role
            raw = json.dumps(dict(financial_authority='NONE', role=role, preserved='legacy fixture'))
            db.execute('INSERT INTO process_generation_counters VALUES(?,?)', (role,generation))
            db.execute('INSERT INTO process_sessions VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (role,generation,token,self.config.product_instance_id,os.getpid(),'sha256:'+'a'*64,
                raw,started,started,12,'STOPPED'))
            db.execute('INSERT INTO process_session_history VALUES(?,?,?,?,?,?,?)',
                (role,generation,token,raw,started,started,'STOPPED'))
        db.commit()
        return db

    def snapshot(self, db):
        return {name: db.execute('SELECT * FROM ' + name + ' ORDER BY role').fetchall()
            for name in ('process_generation_counters','process_sessions','process_session_history')}

    def test_legacy_migration_preserves_exact_rows_history_and_counters_and_is_idempotent(self):
        db = self.legacy_database()
        before = self.snapshot(db)
        self.module._apply_supervision_schema(db)
        self.assertEqual(before, self.snapshot(db))
        receipt = db.execute('SELECT * FROM process_supervision_schema').fetchall()
        self.assertEqual(len(receipt), 1)
        self.module._apply_supervision_schema(db)
        self.assertEqual(receipt, db.execute('SELECT * FROM process_supervision_schema').fetchall())
        self.assertEqual(before, self.snapshot(db))
        db.execute("INSERT INTO process_generation_counters VALUES('runtime',1)")
        db.execute("INSERT INTO process_generation_counters VALUES('cloud',1)")
        db.commit()
        self.module._apply_supervision_schema(db)
        self.assertEqual(db.execute("SELECT generation FROM process_generation_counters WHERE role='runtime'").fetchone()[0],1)

    def test_migration_rollback_keeps_legacy_schema_rows_and_no_partial_receipt(self):
        class FaultConnection(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                if sql.strip().startswith('ALTER TABLE process_sessions_v0_2 RENAME'):
                    raise sqlite3.OperationalError('CONTROLLED_MIGRATION_RENAME_FAILURE')
                return super().execute(sql, *args, **kwargs)
        db = self.legacy_database(FaultConnection)
        before = self.snapshot(db)
        with self.assertRaises(sqlite3.OperationalError):
            self.module._apply_supervision_schema(db)
        self.assertEqual(before, self.snapshot(db))
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(names, set(before))
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO process_generation_counters VALUES('runtime',1)")
        db.rollback()

    def test_changed_migration_digest_receipt_is_fail_closed(self):
        db = self.legacy_database()
        self.module._apply_supervision_schema(db)
        db.execute("UPDATE process_supervision_schema SET sha256='sha256:' || ?", ('0'*64,))
        db.commit()
        before = self.snapshot(db)
        with self.assertRaises(self.module.SupervisionError):
            self.module._apply_supervision_schema(db)
        self.assertEqual(before, self.snapshot(db))

    def test_unknown_existing_column_is_rejected_without_discarding_data(self):
        db = self.legacy_database()
        db.execute("ALTER TABLE process_sessions ADD COLUMN unknown_owner_data TEXT DEFAULT 'preserve-me'")
        db.commit()
        before = self.snapshot(db)
        with self.assertRaises(self.module.SupervisionError):
            self.module._apply_supervision_schema(db)
        self.assertEqual(before, self.snapshot(db))

    def test_unknown_owned_index_or_trigger_is_rejected_and_preserved(self):
        db = self.legacy_database()
        before = self.snapshot(db)
        objects = (
            ('index','legacy_index','CREATE INDEX legacy_index ON process_sessions(pid)'),
            ('trigger','legacy_trigger','CREATE TRIGGER legacy_trigger BEFORE DELETE ON process_sessions BEGIN SELECT 1; END'),
        )
        for kind, name, sql in objects:
            with self.subTest(kind=kind):
                db.execute(sql)
                db.commit()
                with self.assertRaises(self.module.SupervisionError):
                    self.module._apply_supervision_schema(db)
                self.assertEqual(before, self.snapshot(db))
                self.assertEqual(db.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0],sql)
                db.execute('DROP ' + kind + ' ' + name)
                db.commit()

    def test_unknown_unnamed_unique_constraint_is_rejected_without_discarding_it(self):
        db = sqlite3.connect(self.root / 'unknown-constraint.sqlite')
        self.addCleanup(db.close)
        legacy = Path(self.module.__file__).parents[1] / 'migrations/0006_process_supervision.sql'
        changed = legacy.read_text(encoding='utf-8').replace('pid INTEGER NOT NULL,', 'pid INTEGER NOT NULL UNIQUE,')
        db.executescript(changed)
        before = db.execute("SELECT name,sql FROM sqlite_master ORDER BY name").fetchall()
        with self.assertRaises(self.module.SupervisionError):
            self.module._apply_supervision_schema(db)
        self.assertEqual(before, db.execute("SELECT name,sql FROM sqlite_master ORDER BY name").fetchall())

    def test_matching_receipt_does_not_accept_changed_same_column_target_constraints(self):
        db = self.legacy_database()
        self.module._apply_supervision_schema(db)
        receipt = db.execute('SELECT * FROM process_supervision_schema').fetchall()
        db.execute('ALTER TABLE process_generation_counters RENAME TO original_counters')
        db.execute('CREATE TABLE process_generation_counters (role TEXT PRIMARY KEY,generation INTEGER NOT NULL)')
        db.execute('INSERT INTO process_generation_counters SELECT * FROM original_counters')
        db.execute('DROP TABLE original_counters')
        db.commit()
        before = self.snapshot(db)
        with self.assertRaises(self.module.SupervisionError):
            self.module._apply_supervision_schema(db)
        self.assertEqual(before, self.snapshot(db))
        self.assertEqual(receipt, db.execute('SELECT * FROM process_supervision_schema').fetchall())

    def test_owned_migration_digest_is_stable_across_lf_and_crlf_packaging(self):
        db = self.legacy_database()
        self.module._apply_supervision_schema(db)
        receipt = db.execute('SELECT * FROM process_supervision_schema').fetchall()
        source = Path(self.module.__file__).parents[1] / 'migrations'
        alternate = self.root / 'packaged/migrations'
        alternate.mkdir(parents=True)
        for name in ('0006_process_supervision.sql','0008_runtime_process_supervision.sql'):
            original = (source / name).read_text(encoding='utf-8')
            (alternate / name).write_bytes(original.replace('\n','\r\n').encode('utf-8'))
        with mock.patch.object(self.module, '__file__', str(self.root / 'packaged/platform/supervision.py')):
            self.module._apply_supervision_schema(db)
        self.assertEqual(receipt, db.execute('SELECT * FROM process_supervision_schema').fetchall())

    def test_migration_rejects_nested_transaction_without_rolling_back_caller(self):
        db = self.legacy_database()
        db.execute("UPDATE process_generation_counters SET generation=10 WHERE role='control'")
        with self.assertRaises(self.module.SupervisionError):
            self.module._apply_supervision_schema(db)
        self.assertTrue(db.in_transaction)
        self.assertEqual(db.execute("SELECT generation FROM process_generation_counters WHERE role='control'").fetchone()[0],10)
        db.rollback()

    def test_new_database_keeps_role_generation_and_state_constraints(self):
        db = sqlite3.connect(self.root / 'new.sqlite')
        self.addCleanup(db.close)
        self.module._apply_supervision_schema(db)
        for role, generation in (('unknown',1), ('runtime',0), ('cloud',-1)):
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO process_generation_counters VALUES(?,?)', (role,generation))
            db.rollback()
        with self.session('runtime') as owner:
            with closing(sqlite3.connect(owner.path)) as actual:
                with self.assertRaises(sqlite3.IntegrityError):
                    actual.execute("UPDATE process_sessions SET state='PERMISSION_GRANTED' WHERE role='runtime'")
                actual.rollback()
            owner.require_current()

    def test_existing_control_owner_keeps_token_and_heartbeat_when_runtime_schema_is_applied(self):
        # Only initialize with the unchanged legacy script, exactly as the old
        # owner did. Its real lifetime lock and heartbeat remain active while
        # the new runtime owner performs the additive migration.
        legacy = Path(self.module.__file__).parents[1] / 'migrations/0006_process_supervision.sql'
        with mock.patch.object(self.module, '_apply_supervision_schema',
                side_effect=lambda db: db.executescript(legacy.read_text(encoding='utf-8'))):
            control = self.session('control').__enter__()
        try:
            token = control.identity['process_generation_id']
            previous = control.health()['heartbeat_sequence']
            with closing(sqlite3.connect(control.path)) as db:
                self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='process_supervision_schema'").fetchone())
            with self.session('runtime') as runtime:
                self.assertEqual(control.health()['process_generation_id'], token)
                self.wait_heartbeat(control, previous)
                runtime.require_current()
        finally:
            control.__exit__()
