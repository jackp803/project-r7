"""Explicit product mode through normal entries; synthetic inputs, no authority rows."""
from contextlib import redirect_stdout
import importlib
import io
import json
import hashlib
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from application import cli
from application.config import ConfigError, load_config
from registry import EvidenceGateError
from tests.application import test_research_setup_flow as normal


class FixtureProductModeTests(normal.ResearchSetupFlowTests):
    def initialize(self):
        result = self.call(['init-profile', '--config', str(self.config_path),
            '--data-root', str(self.data), '--cloud-root', str(self.cloud),
            '--instance-id', 'normal-fixture-mode', '--execution-mode', 'FIXTURE'])
        self.assertEqual(result['namespace'], 'FIXTURE')
        self.assertEqual(result['runtime'], 'NOT_STARTED')
        config = load_config(self.config_path)
        self.assertEqual(config.execution_mode, 'FIXTURE')
        return config

    def prepare(self, outcome='CANDIDATE'):
        config = super().prepare(outcome)
        self.assertFalse(config.database_path.exists())
        from application.datasets.catalog import canonical, digest
        values = {}
        for name in ('dataset', 'split', 'cost', 'risk'):
            path = self.data/(name+'.json')
            value = json.loads(path.read_bytes())
            value['namespace'] = 'FIXTURE'
            path.write_text(canonical(value), encoding='utf-8')
            values[name] = value
        for name in ('research', 'robustness'):
            path = self.data/(name+'.json')
            value = json.loads(path.read_bytes())
            value.update(namespace='FIXTURE',
                split_policy_hash=digest(canonical(values['split']).encode()),
                cost_policy_hash=digest(canonical(values['cost']).encode()))
            path.write_text(canonical(value), encoding='utf-8')
        return config

    def app(self, config):
        assets = self.root/'ui'
        (assets/'assets').mkdir(parents=True, exist_ok=True)
        (assets/'index.html').write_text('SOURCE_FIXTURE_MODE', encoding='utf-8')
        return importlib.import_module('application.entrypoints').create_local_app(config, asset_root=assets)

    def relabel(self):
        value = json.loads(self.config_path.read_bytes())
        value['execution_mode'] = 'LOCAL_RESEARCH'
        self.config_path.write_text(json.dumps(value), encoding='utf-8')
        return load_config(self.config_path)

    def test_initialized_e6_cannot_be_relabelled_by_changing_product_mode(self):
        config = self.initialize()
        self.app(config)
        before = config.database_path.read_bytes()
        with self.assertRaises(EvidenceGateError):
            self.app(self.relabel())
        self.assertEqual(config.database_path.read_bytes(), before)

    def test_public_enrollment_cannot_relabel_existing_authentication_store(self):
        self.initialize()
        secret = 'synthetic-fixture-product-password-2026'
        with patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', side_effect=[secret,secret]):
            self.call(['enroll-owner','--config',str(self.config_path),'--username','fixture-owner'])
        path = self.data/'local-auth.sqlite'
        before = path.read_bytes()
        self.relabel()
        with patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', side_effect=[secret,secret]):
            with self.assertRaises(ValueError):
                cli.main(['enroll-owner','--config',str(self.config_path),'--username','another-owner'])
        self.assertEqual(path.read_bytes(), before)

    def test_actual_database_restore_preserves_fixture_mode_and_inhibition(self):
        config = self.initialize()
        self.app(config)
        backup, target = self.root/'private-backup', self.root/'restored-generation'
        self.call(['backup-databases','--config',str(self.config_path),'--destination',str(backup)])
        result = self.call(['restore-databases','--config',str(self.config_path),
            '--backup',str(backup),'--destination',str(target)])
        self.assertEqual(result['runtime_new_exposure'], 'INHIBITED')
        restored = load_config(target/'restored-product.json')
        self.assertEqual(restored.execution_mode, 'FIXTURE')
        self.assertTrue(restored.diagnostic_only)
        self.assertFalse(restored.paper_runtime_enabled)
        self.assertIsNone(restored.cloud_root)
        app = self.app(restored)
        self.assertEqual(app.state.local_owners.namespace, 'FIXTURE')
        from application.platform.restoration import require_valid_restoration
        self.assertEqual(require_valid_restoration(restored)['runtime_new_exposure'], 'INHIBITED')

    def test_wrong_namespace_inputs_are_rejected_without_publication(self):
        config = self.prepare()
        path = self.data/'risk.json'
        value = json.loads(path.read_bytes())
        value['namespace'] = 'LOCAL_RESEARCH'
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.configure()
        self.assertFalse((self.data/'owner-selections.json').exists())
        self.assertFalse(config.database_path.exists())


class DefaultAndUnsupportedModeTests(unittest.TestCase):
    setUp = normal.ResearchSetupFlowTests.setUp
    call = normal.ResearchSetupFlowTests.call
    initialize = normal.ResearchSetupFlowTests.initialize
    app = FixtureProductModeTests.app

    @staticmethod
    def legacy_hash(config):
        # Exact pre-mode v0.2 serialization convention; only the legacy
        # producer seam is selected in the two compatibility tests below.
        names = ('schema_version','product_instance_id','local_data_root','cloud_root',
            'database_path','scan_interval','research_worker_count','control_api_host',
            'control_api_port','diagnostic_only','paper_runtime_enabled')
        values = {key:str(getattr(config,key)) if isinstance(getattr(config,key),Path)
            else getattr(config,key) for key in names}
        raw = json.dumps(values,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
        return 'sha256:'+hashlib.sha256(raw).hexdigest()

    def test_default_mode_preserves_legacy_commitment_and_fixture_mode_is_distinct(self):
        from application.platform.supervision import config_hash
        config = self.initialize()
        self.assertEqual(config_hash(config),self.legacy_hash(config))
        self.assertNotEqual(config_hash(replace(config,execution_mode='FIXTURE')),self.legacy_hash(config))

    def test_actual_legacy_backup_verifies_and_restores_with_unchanged_inhibition(self):
        config = self.initialize()
        self.app(config)
        from application.platform import backup as module
        backup, target = self.root/'legacy-backup', self.root/'legacy-restored'
        with patch.object(module,'config_hash',self.legacy_hash):
            self.call(['backup-databases','--config',str(self.config_path),'--destination',str(backup)])
        self.call(['verify-database-backup','--config',str(self.config_path),'--destination',str(backup)])
        self.call(['restore-databases','--config',str(self.config_path),'--backup',str(backup),'--destination',str(target)])
        restored = load_config(target/'restored-product.json')
        from application.platform.restoration import require_valid_restoration
        self.assertEqual(require_valid_restoration(restored)['status'],'RESTORED_INHIBITED')
        self.assertEqual(restored.execution_mode,'LOCAL_RESEARCH')
        self.assertEqual(self.app(restored).state.local_owners.namespace,'LOCAL_RESEARCH')

    def test_actual_legacy_restoration_marker_still_requires_reconciliation(self):
        config = self.initialize()
        self.app(config)
        from application.platform import backup as backup_module, database_restore as restore_module
        backup, target = self.root/'legacy-backup', self.root/'legacy-restored'
        with patch.object(backup_module,'config_hash',self.legacy_hash),patch.object(restore_module,'config_hash',self.legacy_hash):
            self.call(['backup-databases','--config',str(self.config_path),'--destination',str(backup)])
            self.call(['restore-databases','--config',str(self.config_path),'--backup',str(backup),'--destination',str(target)])
        profile = target/'restored-product.json'
        value = json.loads(profile.read_bytes())
        value.pop('execution_mode')
        profile.write_text(json.dumps(value),encoding='utf-8')
        restored = load_config(profile)
        from application.platform.restoration import require_valid_restoration
        status = require_valid_restoration(restored)
        self.assertEqual(status['status'],'RESTORED_INHIBITED')
        self.assertEqual(status['runtime_new_exposure'],'INHIBITED')
        self.assertEqual(status['reconciliation'],'REQUIRED')
        self.assertEqual(self.app(restored).state.local_owners.namespace,'LOCAL_RESEARCH')
    def test_legacy_profile_without_mode_remains_local_research(self):
        config = self.initialize()
        value = json.loads(self.config_path.read_bytes())
        value.pop('execution_mode', None)
        self.config_path.write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual(load_config(self.config_path).execution_mode, 'LOCAL_RESEARCH')

    def test_unknown_or_live_modes_fail_before_profile_or_database_initialization(self):
        for mode in ('LIVE', 'SHADOW', 'PAPER', 'fixture', ''):
            with self.subTest(mode=mode), redirect_stdout(io.StringIO()), patch('sys.stderr', io.StringIO()):
                with self.assertRaises(SystemExit):
                    cli.main(['init-profile','--config',str(self.config_path),'--data-root',str(self.data),
                        '--instance-id','unsupported-mode','--execution-mode',mode])
            self.assertFalse(self.config_path.exists())
            self.assertFalse(self.data.exists())
        self.initialize()
        value = json.loads(self.config_path.read_bytes())
        value['execution_mode'] = 'LIVE'
        self.config_path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaises(ConfigError):
            load_config(self.config_path)
