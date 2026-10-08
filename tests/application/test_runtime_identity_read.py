"""Read actual owned supervision fixtures; never attach a PAPER/trading worker."""
from contextlib import closing
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application.config import ProductConfig
from application.platform import supervision


class RuntimeIdentityReadTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 runtime identity ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = ProductConfig('r7-product-config-v0.2', 'identity-read-fixture',
            self.root / 'local', None, self.root / 'local/canonical.sqlite3')
        self.now = datetime(2026, 10, 8, tzinfo=timezone.utc)
        self.path = self.config.local_data_root / 'process-supervision.sqlite'
        self.assertIsNotNone(importlib.util.find_spec('application.platform.runtime_identity'),
            'Missing bounded read-only runtime identity accessor')
        self.module = importlib.import_module('application.platform.runtime_identity')

    def owner(self, role='runtime'):
        return supervision.ProcessSupervisor(self.config, role, heartbeat_interval=5,
            clock=lambda: self.now)

    def read(self, **options):
        return self.module.read_runtime_identity(self.config, now=self.now, **options)

    def change(self, sql, values=()):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(sql, values)

    def logical_snapshot(self):
        with closing(sqlite3.connect(self.path)) as db:
            return {table: db.execute('SELECT * FROM ' + table + ' ORDER BY 1,2').fetchall()
                for table in ('process_sessions', 'process_session_history',
                              'process_generation_counters', 'process_supervision_schema')}

    def identity(self, owner, **changes):
        value = dict(owner.identity, **changes)
        self.raw_identity(json.dumps(value, sort_keys=True, separators=(',', ':')))

    def raw_identity(self, raw):
        self.change("UPDATE process_sessions SET identity_json=? WHERE role='runtime'", (raw,))
        self.change("UPDATE process_session_history SET identity_json=? WHERE role='runtime'", (raw,))

    def denied(self, **options):
        with self.assertRaises(self.module.RuntimeIdentityUnavailable):
            self.read(**options)

    def test_missing_runtime_does_not_create_local_directory_or_database(self):
        self.denied()
        self.assertFalse(self.config.local_data_root.exists())

    def test_other_actual_owner_does_not_create_runtime_generation(self):
        with self.owner('control'):
            before = self.logical_snapshot()
            self.denied()
            self.assertEqual(self.logical_snapshot(), before)

    def test_current_identity_is_immutable_and_read_does_not_attach_or_write(self):
        with self.owner() as owner:
            before = self.logical_snapshot()
            snapshot = self.read()
            self.assertEqual(dict(snapshot.identity), owner.identity)
            self.assertEqual(snapshot.identity['generation'], 1)
            self.assertEqual(snapshot.identity['financial_authority'], 'NONE')
            self.assertEqual(snapshot.identity['restart_admission'], 'RECONCILIATION_REQUIRED')
            self.assertEqual(snapshot.observed_at, '2026-10-08T00:00:00.000000Z')
            self.assertEqual(self.logical_snapshot(), before)
            with self.assertRaises(TypeError):
                snapshot.identity['generation'] = 900
            with self.assertRaises(FrozenInstanceError):
                snapshot.heartbeat_sequence = 900

    def test_stopped_owner_cannot_supply_current_identity(self):
        with self.owner():
            self.read()
        before = self.logical_snapshot()
        self.denied()
        self.assertEqual(self.logical_snapshot(), before)

    def test_restart_returns_new_actual_generation_and_leaves_old_snapshot_unchanged(self):
        with self.owner():
            first = self.read()
        with self.owner():
            second = self.read()
        self.assertEqual(first.identity['generation'], 1)
        self.assertEqual(second.identity['generation'], 2)
        self.assertNotEqual(first.identity['process_generation_id'], second.identity['process_generation_id'])

    def test_changed_configuration_cannot_read_old_runtime_as_current(self):
        with self.owner():
            changed = replace(self.config, scan_interval=self.config.scan_interval + 1)
            with self.assertRaises(self.module.RuntimeIdentityUnavailable):
                self.module.read_runtime_identity(changed, now=self.now)

    def test_stale_heartbeat_is_denied_without_renewal(self):
        with self.owner():
            before = self.logical_snapshot()
            with self.assertRaises(self.module.RuntimeIdentityUnavailable):
                self.module.read_runtime_identity(self.config, now=self.now + timedelta(seconds=16))
            self.assertEqual(self.logical_snapshot(), before)

    def test_future_heartbeat_is_denied(self):
        with self.owner():
            with self.assertRaises(self.module.RuntimeIdentityUnavailable):
                self.module.read_runtime_identity(self.config, now=self.now - timedelta(seconds=1))

    def test_generation_counter_drift_is_denied(self):
        with self.owner():
            self.change("UPDATE process_generation_counters SET generation=2 WHERE role='runtime'")
            self.denied()

    def test_history_identity_mismatch_is_denied(self):
        with self.owner():
            self.change("UPDATE process_session_history SET identity_json='{}' WHERE role='runtime'")
            self.denied()

    def test_duplicate_json_keys_are_denied_even_when_history_matches(self):
        with self.owner() as owner:
            raw = json.dumps(owner.identity)
            self.raw_identity('{"generation":999,' + raw[1:])
            self.denied()

    def test_oversized_identity_is_denied_before_json_decode(self):
        with self.owner():
            self.raw_identity(' ' * (16 * 1024 + 1))
            self.denied()

    def test_identity_types_software_commitments_and_authority_are_validated(self):
        with self.owner() as owner:
            for changes in ({'executable_revision': 'a' * 39},
                            {'implementation_hash': 'sha256:' + 'g' * 64},
                            {'pid': True}, {'generation': True}, {'provider_requests': True},
                            {'credentials': 'PRESENT'}, {'capital': 'PRESENT'},
                            {'financial_authority': 'LIVE'}, {'restart_admission': 'READY'},
                            {'unknown': {}}, {'started_at': '2026-10-08T00:00:00Z'}):
                with self.subTest(changes=changes):
                    self.identity(owner, **changes)
                    self.denied()

    def test_record_columns_cannot_disagree_with_persisted_identity(self):
        with self.owner() as owner:
            for changes in ({'product_instance_id': 'other-instance'},
                            {'config_hash': 'sha256:' + 'b' * 64},
                            {'process_generation_id': '00000000-0000-4000-8000-000000000000'},
                            {'role': 'control'}, {'generation': 2}):
                with self.subTest(changes=changes):
                    self.identity(owner, **changes)
                    self.denied()

    def test_numeric_process_token_is_denied_with_the_typed_error(self):
        with self.owner() as owner:
            self.identity(owner, process_generation_id=1)
            self.denied()

    def test_numeric_environment_provenance_is_not_returned_as_valid_facts(self):
        with self.owner() as owner:
            for field in ('os', 'os_version', 'architecture', 'python'):
                with self.subTest(field=field):
                    self.identity(owner, **{field: 1})
                    self.denied()

    def test_changed_schema_is_denied_without_migration(self):
        with self.owner():
            self.change('CREATE INDEX unexpected_runtime_index ON process_sessions(pid)')
            before = self.logical_snapshot()
            self.denied()
            self.assertEqual(self.logical_snapshot(), before)

    def test_changed_migration_commitment_is_denied_without_repair(self):
        with self.owner():
            self.change("UPDATE process_supervision_schema SET sha256='changed'")
            before = self.logical_snapshot()
            self.denied()
            self.assertEqual(self.logical_snapshot(), before)

    def test_absent_process_is_denied_despite_recent_consistent_rows(self):
        with self.owner() as owner:
            self.identity(owner, pid=2147483647)
            self.change("UPDATE process_sessions SET pid=2147483647 WHERE role='runtime'")
            self.denied()

    def test_oversized_pid_cannot_wrap_to_the_current_native_process(self):
        with self.owner() as owner:
            oversized = 2**32 + os.getpid()
            self.identity(owner, pid=oversized)
            self.change("UPDATE process_sessions SET pid=? WHERE role='runtime'", (oversized,))
            self.denied()

    def test_native_identity_shape_preserves_build_but_grants_no_permission(self):
        # Protocol fixture only: this is not native package/worker execution.
        native = dict(supervision.capture_provenance(), build_hash='sha256:' + 'b' * 64,
            distribution_profile='r7-native-distribution-v0.2', worktree='UNAVAILABLE',
            financial_authority='NONE')
        with patch.object(supervision, 'capture_provenance', return_value=native):
            with self.owner() as owner:
                snapshot = self.read()
                self.assertEqual(dict(snapshot.identity), owner.identity)
                self.assertEqual(snapshot.identity['build_hash'], 'sha256:' + 'b' * 64)
                self.assertEqual(snapshot.identity['financial_authority'], 'NONE')
                self.identity(owner, build_hash='bad')
                self.denied()

    def test_invalid_clock_and_policy_do_not_create_runtime_storage(self):
        for age in (True, 0, 61, 1.5):
            with self.subTest(age=age), self.assertRaises(ValueError):
                self.read(max_age_seconds=age)
        with self.assertRaises(ValueError):
            self.module.read_runtime_identity(self.config, now=datetime(2026, 10, 8))
        self.assertFalse(self.config.local_data_root.exists())


if __name__ == '__main__':
    unittest.main()
