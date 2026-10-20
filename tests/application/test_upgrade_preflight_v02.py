"""genuine missing-API RED comes after valid bundle."""
import importlib
import unittest

from tests.application.upgrade_preflight_fixture import (
    ROLES,make_verified_bundle,source_database_hashes,bundle_hashes)


class UpgradePreflightV02Tests(unittest.TestCase):
    def test_result_binds_actual_target_source_configuration_and_verified_backup_bytes(self):
        import hashlib,json
        from application.platform.supervision import config_hash
        from strategy.v02.capabilities import _revision
        c=make_verified_bundle(self)
        module=importlib.import_module('application.platform.upgrade_preflight')
        result=module.preflight_product_upgrade(c.config,c.backup,config_path=c.config_path)
        manifest=(c.backup/'manifest.json').read_bytes()
        self.assertEqual('r7-product-upgrade-preflight-v0.2',result['schema_version'])
        self.assertEqual(_revision(),result['target_provenance']['implementation_hash'])
        self.assertRegex(result['target_provenance']['executable_revision'],r'^[0-9a-f]{40}$')
        self.assertEqual('LOCAL',result['target_provenance']['execution'])
        self.assertEqual(config_hash(c.config),result['source_config_hash'])
        self.assertEqual(json.loads(manifest)['backup_id'],result['backup_id'])
        self.assertEqual('sha256:'+hashlib.sha256(manifest).hexdigest(),result['backup_manifest_sha256'])
        self.assertEqual(c.source_hashes,source_database_hashes(c.config))
        self.assertEqual(c.backup_hashes,bundle_hashes(c.backup))

    def test_actual_supported_eight_role_inventory_preflight_is_readonly(self):
        c=make_verified_bundle(self)
        # Deliberately deferred until genuine source/verified backup exists.
        module=importlib.import_module('application.platform.upgrade_preflight')
        result=module.preflight_product_upgrade(c.config,c.backup,
            config_path=c.config_path,timeout_seconds=30)
        self.assertEqual('COMPATIBLE_FOR_INHIBITED_CLONE',result['status'])
        self.assertEqual('NONE',result['financial_authority'])
        self.assertEqual(0,result['database_mutations'])
        self.assertEqual(0,result['owner_starts'])
        self.assertEqual(ROLES,set(result['roles']))
        for role in sorted(ROLES):
            with self.subTest(role=role):
                self.assertEqual('ABSENT' if role in c.absent else 'COMPATIBLE',
                    result['roles'][role]['status'])
        self.assertEqual((),tuple(result['roles']['canonical']['pending']))
        self.assertEqual(c.source_hashes,source_database_hashes(c.config))
        self.assertEqual(c.backup_hashes,bundle_hashes(c.backup))

    def test_genuine_changed_queue_schema_backup_verifies_but_preflight_and_restore_refuse_before_target(self):
        c=make_verified_bundle(self,mismatched_queue=True)
        # Integrity-valid actual backup is not target-schema compatibility.
        module=importlib.import_module('application.platform.upgrade_preflight')
        with self.assertRaisesRegex(module.UpgradePreflightError,
                '^UPGRADE_PREFLIGHT_SCHEMA_UNSUPPORTED$'):
            module.preflight_product_upgrade(c.config,c.backup,
                config_path=c.config_path,timeout_seconds=30)
        from application.platform.database_restore import RestoreError,_restore_backup
        target=c.fixture.base/'must-not-be-created'
        self.assertFalse(target.exists())
        # Exact same underlying owner path as restore_product_backup; assert
        # existing RestoreError envelope rather than invalid manifest/FK credit.
        with self.assertRaisesRegex(RestoreError,'^PRIVATE_DATABASE_RESTORE_FAILED$'):
            _restore_backup(c.config,c.backup,target,config_path=c.config_path,
                timeout_seconds=30,product_data=True)
        self.assertFalse(target.exists())
        self.assertEqual(c.source_hashes,source_database_hashes(c.config))
        self.assertEqual(c.backup_hashes,bundle_hashes(c.backup))
