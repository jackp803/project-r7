"""Actual workflow tests: actual synthetic all-present/schema/prefix/locks."""
from contextlib import ExitStack
import time
import unittest

from application.platform.backup import BackupError
from application.platform.database_restore import RestoreError,_restore_backup
from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from application.platform.supervision import PROCESS_ROLES
from application.platform.upgrade_preflight import (
    UpgradePreflightError,preflight_product_upgrade,_preflight_verified_databases)
from storage._sqlite_registry import _MIGRATIONS_DIR
from tests.application.upgrade_preflight_fixture import ROLES,source_database_hashes,bundle_hashes
from tests.application.upgrade_preflight_complete_fixture import make_all_present_bundle,make_prefix19_bundle


def _unchanged(testcase,c):
    testcase.assertEqual(c.source_hashes,source_database_hashes(c.config))
    testcase.assertEqual(c.backup_hashes,bundle_hashes(c.backup))


class UpgradePreflightCompleteV02Tests(unittest.TestCase):
    def test_real_prefix_restore_and_product_composition_migrate_only_inhibited_clone(self):
        from contextlib import closing
        import sqlite3
        from application.config import load_config
        from application.entrypoints import create_local_app
        from application.platform.product_backup import restore_product_backup
        c=make_prefix19_bundle(self)
        target=c.fixture.base/'fresh-prefix19-inhibited-clone'
        result=restore_product_backup(c.config,c.backup,target,config_path=c.config_path)
        self.assertEqual('PRODUCT_DATA_RESTORE_STAGED',result['status'])
        self.assertEqual('INHIBITED',result['runtime_new_exposure'])
        self.assertEqual('NONE',result['financial_authority'])
        config=load_config(target/'restored-product.json')
        with closing(sqlite3.connect(config.database_path)) as db:
            self.assertEqual(19,db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0])
        app=create_local_app(config)
        self.assertTrue(app.state.local_owners.config.diagnostic_only)
        self.assertFalse(app.state.local_owners.config.paper_runtime_enabled)
        self.assertIsNone(app.state.local_owners.config.cloud_root)
        health=app.state.local_owners.control_services().view('health')
        self.assertEqual('RESTORED_INHIBITED',health['restoration']['status'])
        self.assertEqual('INHIBITED',health['restoration']['runtime_new_exposure'])
        self.assertFalse(health['live_authorized'])
        with closing(sqlite3.connect(config.database_path)) as db:
            self.assertEqual(tuple(sorted(p.name for p in _MIGRATIONS_DIR.glob('*.sql'))),
                tuple(row[0] for row in db.execute('SELECT migration_name FROM schema_migrations ORDER BY migration_name')))
            self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual('ok',db.execute('PRAGMA quick_check').fetchone()[0])
        _unchanged(self,c)

    def test_all_eight_actual_owner_schemas_present_preflight_has_no_source_or_bundle_effects(self):
        c=make_all_present_bundle(self)
        result=preflight_product_upgrade(c.config,c.backup,config_path=c.config_path,timeout_seconds=30)
        self.assertEqual('COMPATIBLE_FOR_INHIBITED_CLONE',result['status'])
        self.assertEqual('NONE',result['financial_authority'])
        self.assertEqual((0,0),(result['database_mutations'],result['owner_starts']))
        self.assertEqual(ROLES,set(result['roles']))
        self.assertEqual({role:'COMPATIBLE' for role in ROLES},
            {role:row['status'] for role,row in result['roles'].items()})
        known=tuple(sorted(p.name for p in _MIGRATIONS_DIR.glob('*.sql')))
        self.assertEqual(known,tuple(result['roles']['canonical']['applied']))
        self.assertEqual((),tuple(result['roles']['canonical']['pending']))
        _unchanged(self,c)

    def test_valid_normal_backups_of_changed_research_schema_control_version_or_supervision_receipt_refuse_before_restore(self):
        for vector in ('research-index','control-user-version','supervision-receipt'):
            with self.subTest(vector=vector):
                c=make_all_present_bundle(self,mutation=vector)
                with self.assertRaisesRegex(UpgradePreflightError,'^UPGRADE_PREFLIGHT_SCHEMA_UNSUPPORTED$'):
                    preflight_product_upgrade(c.config,c.backup,config_path=c.config_path,timeout_seconds=30)
                target=c.fixture.base/'must-not-create-restored-generation'
                self.assertFalse(target.exists())
                with self.assertRaisesRegex(RestoreError,'^PRIVATE_DATABASE_RESTORE_FAILED$'):
                    _restore_backup(c.config,c.backup,target,config_path=c.config_path,
                        timeout_seconds=30,product_data=True)
                self.assertFalse(target.exists())
                _unchanged(self,c)

    def test_actual_prefix19_source_normal_backup_reports_only_pending_suffix_without_migration(self):
        c=make_prefix19_bundle(self)
        result=preflight_product_upgrade(c.config,c.backup,config_path=c.config_path,timeout_seconds=30)
        self.assertEqual('COMPATIBLE_FOR_INHIBITED_CLONE',result['status'])
        self.assertEqual('NONE',result['financial_authority'])
        self.assertEqual((0,0),(result['database_mutations'],result['owner_starts']))
        known=tuple(sorted(p.name for p in _MIGRATIONS_DIR.glob('*.sql')))
        cap=known.index('0019_paper_operational_selections.sql')+1
        self.assertEqual(19,cap)
        self.assertGreater(len(known),cap)
        self.assertEqual(ROLES,set(result['roles']))
        self.assertEqual(known[:cap],tuple(result['roles']['canonical']['applied']))
        self.assertEqual(known[cap:],tuple(result['roles']['canonical']['pending']))
        self.assertEqual('COMPATIBLE',result['roles']['canonical']['status'])
        for role in ROLES-{'canonical'}:
            self.assertEqual('ABSENT',result['roles'][role]['status'])
        _unchanged(self,c)

    def test_actual_held_role_and_expired_reader_deadline_refuse_without_mutating_valid_bundle(self):
        c=make_all_present_bundle(self)
        target=c.fixture.base/'must-remain-absent'
        with ProcessScopeLock('research:'+c.config.product_instance_id,
                lock_root=operational_lock_root(c.config)):
            with self.assertRaisesRegex(UpgradePreflightError,'^UPGRADE_PREFLIGHT_UNAVAILABLE$'):
                preflight_product_upgrade(c.config,c.backup,config_path=c.config_path,timeout_seconds=30)
            _unchanged(self,c)
        # Parameter-bound denial is separate from actual expired internal budget.
        with self.assertRaisesRegex(UpgradePreflightError,'^UPGRADE_PREFLIGHT_DEADLINE_REQUIRED$'):
            preflight_product_upgrade(c.config,c.backup,config_path=c.config_path,timeout_seconds=0)
        _unchanged(self,c)
        # Same owner-held/verified-manifest preconditions as restore. No clock
        # patch, wait/sleep, factory answer or threshold increase is involved.
        with ExitStack() as locks:
            for role in PROCESS_ROLES:
                locks.enter_context(ProcessScopeLock(role+':'+c.config.product_instance_id,
                    lock_root=operational_lock_root(c.config)))
            with self.assertRaisesRegex(BackupError,'^DATABASE_BACKUP_DEADLINE_EXCEEDED$'):
                _preflight_verified_databases(c.config,c.backup/'databases',c.manifest,
                    time.monotonic()-1,include_settings=True)
        self.assertFalse(target.exists())
        _unchanged(self,c)
        # Prove all prior lock paths released: normal actual request works again.
        self.assertEqual('COMPATIBLE_FOR_INHIBITED_CLONE',preflight_product_upgrade(
            c.config,c.backup,config_path=c.config_path,timeout_seconds=30)['status'])
        _unchanged(self,c)
