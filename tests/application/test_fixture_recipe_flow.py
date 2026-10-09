"""Product-generated synthetic inputs through actual public research entries."""
import importlib
import json
import unittest
from unittest.mock import patch

from application import cli
from application.config import load_config
from application.platform.scope_lock import ProcessScopeLock, ScopeBusy, operational_lock_root
from tests.application import test_research_setup_flow as normal
from tests.application import test_fixture_product_mode as mode


class FixtureRecipeFlowTests(unittest.TestCase):
    setUp = normal.ResearchSetupFlowTests.setUp
    call = normal.ResearchSetupFlowTests.call
    initialize = mode.FixtureProductModeTests.initialize
    app = mode.FixtureProductModeTests.app

    def generate(self, scenario='positive'):
        return self.call(['prepare-fixture','--config',str(self.config_path),'--scenario',scenario])

    def prepare(self, scenario='positive'):
        config = self.initialize()
        result = self.generate(scenario)
        self.assertEqual(result['namespace'], 'FIXTURE')
        self.assertEqual(result['execution_evidence'], 'NOT_RUN')
        self.assertEqual(result['financial_authority'], 'NONE')
        self.profile = self.data/result['selection_profile_ref']
        return config, result

    def configure(self):
        return self.call(['configure-research','--config',str(self.config_path),'--selection-profile',str(self.profile)])

    def flow(self, scenario):
        config, generated = self.prepare(scenario)
        self.assertFalse(config.database_path.exists())
        self.configure()
        secret = 'synthetic-source-recipe-password-2026'
        with patch('sys.stdin.isatty',return_value=True),patch('getpass.getpass',side_effect=[secret,secret]):
            self.call(['enroll-owner','--config',str(self.config_path),'--username','fixture-owner'])
        from fastapi.testclient import TestClient
        with TestClient(self.app(config),base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000)) as client:
            login = client.post('/api/v1/auth/login',json=dict(username='fixture-owner',password=secret,
                command_id='recipe-login',expected_revision=0),headers={'Origin':'http://127.0.0.1:8765'})
            self.assertEqual(login.status_code,200,login.text)
            headers = {'Origin':'http://127.0.0.1:8765','x-r7-csrf':login.json()['csrf_token']}
            scan = client.post('/api/v1/research/scan',json=dict(command_id='recipe-scan',expected_revision=0),headers=headers)
            self.assertEqual(scan.status_code,200,scan.text)
            submission = client.get('/api/v1/submissions/'+generated['submission_id']).json()['data']
            enqueue = client.post('/api/v1/research/runs',json=dict(command_id='recipe-enqueue',
                expected_revision=submission['revision'],submission_id=generated['submission_id'],
                policy_id=generated['policy_id']),headers=headers)
            self.assertEqual(enqueue.status_code,202,enqueue.text)
            job = enqueue.json()['effect_ref'].removeprefix('research-job:')
            completed = self.call(['research-worker','--config',str(self.config_path),'--once'])
            self.assertEqual(completed['status'],'JOB_FINISHED')
            self.assertTrue(completed['tree_reaped'])
            self.assertNotEqual(completed['parent_pid'],completed['child_pid'])
            actual = client.get('/api/v1/research/runs/'+job).json()['data']['payload']
            strategy = client.get('/api/v1/strategies').json()['data']['items'][0]
            return actual, strategy['current_lifecycle_state']

    def test_product_generated_positive_reaches_candidate_through_normal_child(self):
        actual, state = self.flow('positive')
        self.assertEqual(state,'CANDIDATE')
        self.assertEqual(actual['evidence']['sealed_oos'],'PASS')

    def test_product_generated_oos_loss_is_actually_rejected(self):
        actual, state = self.flow('oos-loss')
        self.assertEqual(state,'REJECTED')
        self.assertEqual(actual['evidence']['sealed_oos'],'FAIL')

    def test_product_generated_insufficient_oos_remains_blocked(self):
        actual, state = self.flow('insufficient-oos')
        self.assertEqual(state,'BACKTESTING')
        self.assertEqual(actual['state'],'COMPLETE')
        self.assertEqual(actual['outcome']['status'],'BLOCKED')
        self.assertEqual(actual['evidence']['sealed_oos'],'BLOCKED')

    def test_generation_creates_only_fresh_inputs_and_actual_e2_package(self):
        config, result = self.prepare()
        self.assertFalse(config.database_path.exists())
        self.assertFalse(list(self.data.rglob('*.sqlite*')))
        selected = json.loads(self.profile.read_bytes())
        for key, ref in selected['research_policies'][result['policy_id']].items():
            if key.endswith('_ref'):
                self.assertEqual(json.loads((self.data/ref).read_bytes())['namespace'],'FIXTURE')
        from strategy import parse_strategy_definition
        manifest = next(self.cloud.rglob('manifest.json'))
        parsed = parse_strategy_definition((manifest.parent/'strategy.json').read_bytes())
        self.assertEqual(parsed.symbol,'BTC_USDT_PERP')
        self.assertEqual(json.loads(manifest.read_bytes())['submission_id'],result['submission_id'])
        self.assertEqual(self.configure()['namespace'],'FIXTURE')

    def test_ordinary_mode_rejects_fixture_generation_before_writing_inputs(self):
        normal.ResearchSetupFlowTests.initialize(self)
        with self.assertRaises(ValueError):
            self.generate()
        self.assertFalse(self.data.exists())
        self.assertFalse(self.cloud.exists())

    def reject_installation(self, installation):
        with patch('application.entrypoints.installed_root',return_value=installation):
            with self.assertRaises(ValueError):
                self.generate()
        self.assertFalse(self.data.exists())
        self.assertFalse(self.cloud.exists())

    def test_frozen_installation_cannot_be_used_as_data(self):
        config = self.initialize()
        self.reject_installation(config.local_data_root)

    def test_frozen_installation_cannot_be_used_as_fake_staging(self):
        config = self.initialize()
        self.reject_installation(config.cloud_root)

    def test_existing_inputs_are_never_replaced_by_another_scenario(self):
        self.prepare()
        before = {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError):
            self.generate('oos-loss')
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_all_operational_owners_fence_generation_before_any_fixture_write(self):
        config = self.initialize()
        for role in ('control','research','runtime','cloud'):
            with self.subTest(role=role),ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)):
                with self.assertRaises(ScopeBusy):
                    self.generate()
            self.assertFalse((self.data/'fixture-inputs').exists())
            self.assertFalse(self.cloud.exists())

    def test_restored_generation_cannot_receive_new_fixture_inputs(self):
        config = self.initialize()
        self.app(config)
        backup, target = self.root/'private-backup', self.root/'restored-generation'
        self.call(['backup-databases','--config',str(self.config_path),'--destination',str(backup)])
        self.call(['restore-databases','--config',str(self.config_path),'--backup',str(backup),'--destination',str(target)])
        self.config_path = target/'restored-product.json'
        with self.assertRaises(ValueError):
            self.generate()
        self.assertFalse((target/'fixture-inputs').exists())
