from dataclasses import asdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
import unittest

from application.config import ProductConfig
from application.platform.scope_lock import ProcessScopeLock, ScopeBusy


class ProcessSupervisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 監督 世代 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = ProductConfig('r7-product-config-v0.2', 'supervision-fixture', self.root / '資料',
                                    None, self.root / '資料' / 'canonical.sqlite3')
        self.profile = self.root / '設定.json'
        self.write_profile()

    def write_profile(self, **changes):
        data = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(self.config).items()}
        data.update(changes)
        self.profile.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def module(self):
        return importlib.import_module('application.platform.supervision')

    def session(self, **changes):
        return self.module().ProcessSupervisor(self.config, 'research', config_path=self.profile,
                                               heartbeat_interval=0.05, **changes)

    def test_restart_has_a_new_actual_process_generation_and_never_financial_permission(self):
        with self.session() as first:
            previous = first.identity
            self.assertEqual(first.health()['status'], 'RECENT_HEARTBEAT')
            self.assertEqual(previous['financial_authority'], 'NONE')
            self.assertEqual(previous['config_hash'], self.module().config_hash(self.config))
            self.assertTrue(previous['implementation_hash'].startswith('sha256:'))
        self.assertEqual(first.health()['status'], 'STOPPED')
        with self.session() as successor:
            self.assertGreater(successor.identity['generation'], previous['generation'])
            self.assertNotEqual(successor.identity['process_generation_id'], previous['process_generation_id'])

    def test_heartbeat_thread_advances_while_owner_work_is_blocked(self):
        with self.session() as session:
            before = session.health()['heartbeat_sequence']
            deadline = time.monotonic() + 2
            while session.health()['heartbeat_sequence'] <= before:
                if time.monotonic() > deadline: self.fail('Actual heartbeat thread did not advance')
                time.sleep(0.02)
            session.require_current()

    def test_config_change_inhibits_the_existing_generation_without_renewing_it(self):
        with self.session() as session:
            original = session.identity['process_generation_id']
            self.write_profile(scan_interval=31)
            deadline = time.monotonic() + 2
            while not session.failed:
                if time.monotonic() > deadline: self.fail('Actual configuration change was not detected')
                time.sleep(0.02)
            with self.assertRaises(self.module().SupervisionError): session.require_current()
            self.assertEqual(session.health()['status'], 'CONFIG_CHANGED')
            self.assertEqual(session.identity['process_generation_id'], original)

    def test_second_supervisor_is_denied_before_it_creates_a_database(self):
        with ProcessScopeLock('research:' + self.config.product_instance_id, lock_root=self.root / 'locks'):
            with self.assertRaises(ScopeBusy):
                with self.session(): pass
        self.assertFalse((self.config.local_data_root / 'process-supervision.sqlite').exists())

    def test_stale_and_future_heartbeat_are_explicitly_inhibited(self):
        observed = datetime.now(timezone.utc)
        with self.session(clock=lambda: observed) as session:
            self.assertEqual(session.health(now=observed + timedelta(seconds=20))['status'], 'STALE_HEARTBEAT')
            self.assertEqual(session.health(now=observed - timedelta(seconds=1))['status'], 'CLOCK_REGRESSION')

    def test_a_stolen_durable_generation_cannot_be_renewed_or_cleanly_stopped(self):
        with self.assertRaises(self.module().SupervisionError):
            with self.session() as session:
                with closing(sqlite3.connect(session.path)) as db, db:
                    db.execute("UPDATE process_sessions SET process_generation_id='fixture-successor' WHERE role='research'")
                session.require_current()
        with closing(sqlite3.connect(session.path)) as db:
            self.assertEqual(db.execute("SELECT state FROM process_sessions WHERE role='research'").fetchone()[0], 'RUNNING')

    def test_actual_clock_regression_stops_heartbeat_and_cannot_resume_automatically(self):
        now = [datetime.now(timezone.utc)]
        with self.session(clock=lambda: now[0]) as session:
            now[0] -= timedelta(seconds=10)
            deadline = time.monotonic() + 2
            while not session.failed:
                if time.monotonic() > deadline: self.fail('Clock regression did not inhibit heartbeat')
                time.sleep(0.02)
            self.assertEqual(session.health()['status'], 'CLOCK_REGRESSION')
            now[0] += timedelta(seconds=20)
            with self.assertRaises(self.module().SupervisionError): session.require_current()

    def test_profile_different_from_loaded_config_is_refused_before_start(self):
        self.write_profile(control_api_port=8766)
        with self.assertRaises(self.module().SupervisionError):
            with self.session(): pass
        self.assertFalse((self.config.local_data_root / 'process-supervision.sqlite').exists())
