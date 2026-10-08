"""Public setup and actual normal research composition with newly generated synthetic inputs.

No lifecycle/evidence/approval rows are injected. These are source integration
checks with a local-folder simulation, not native or real-cloud acceptance.
"""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import importlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application import cli
from application.config import ConfigError, load_config
from application.datasets.catalog import canonical, digest
from application.platform.scope_lock import ProcessScopeLock, ScopeBusy, operational_lock_root
from tests.application import cloud_fixtures, dataset_fixtures
from tests.application.test_product_assessment_binding import risk_fixture
from tests.application.test_research_robustness import selected
from tests.validation.robustness_fixtures import subject
from strategy.v02.capabilities import build_capability_snapshot


class ResearchSetupFlowTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='R7 public setup 中文 ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config_path = self.root/'config.json'
        self.data, self.cloud = self.root/'local data', self.root/'cloud simulation'
        self.profile = self.root/'operator selection.json'

    def call(self, arguments):
        with redirect_stdout(io.StringIO()) as output:
            code = cli.main(arguments)
        self.assertEqual(code, 0, output.getvalue())
        return json.loads(output.getvalue())

    def initialize(self):
        result = self.call(['init-profile', '--config', str(self.config_path), '--data-root', str(self.data),
            '--cloud-root', str(self.cloud), '--instance-id', 'public-setup-fixture'])
        self.assertEqual(result['runtime'], 'NOT_STARTED')
        return load_config(self.config_path)

    def prepare(self, outcome='CANDIDATE'):
        config = self.initialize()
        def losses(rows):
            for index, row in enumerate(rows[32:]):
                row.update(open=str(1000000+index), high=str(1000002+index),
                           low=str(999999+index), close=str(1000001+index))
        selected(self.data, losses if outcome=='REJECTED' else None)
        (self.data/'risk.json').write_bytes(dataset_fixtures.encoded(risk_fixture()))
        # Change only fresh, unexecuted generation inputs. No FIXTURE result,
        # journal or financial authority is ever relabeled LOCAL_RESEARCH.
        values = {}
        for name in ('dataset', 'split', 'cost', 'risk'):
            path = self.data/(name+'.json'); value = json.loads(path.read_bytes())
            value['namespace'] = 'LOCAL_RESEARCH'; path.write_text(canonical(value), encoding='utf-8')
            values[name] = value
        for name in ('research', 'robustness'):
            path = self.data/(name+'.json'); value = json.loads(path.read_bytes())
            value.update(namespace='LOCAL_RESEARCH', split_policy_hash=digest(canonical(values['split']).encode()),
                         cost_policy_hash=digest(canonical(values['cost']).encode()))
            if name=='research' and outcome=='INSUFFICIENT': value['minimum_closed_trades']['sealed_oos']=100
            path.write_text(canonical(value), encoding='utf-8')
        self.cloud.mkdir()
        (self.cloud/'.r7-root.json').write_bytes(dataset_fixtures.encoded({'root_id':'synthetic-local-folder'}))
        folder, manifest, _ = cloud_fixtures.package(self.cloud, submission='public-flow-input', version='0.2', definition=subject())
        manifest['capability_snapshot_hash']=build_capability_snapshot().snapshot_hash
        (folder/'manifest.json').write_bytes(dataset_fixtures.encoded(manifest))
        policy = dict(dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json',
            research_policy_ref='research.json',robustness_policy_ref='robustness.json',risk_policy_ref='risk.json',
            family_id='public-setup-family',seed=42,requested_dataset_profile='fixture-data',
            requested_validation_profile='diagnostic',requested_robustness_profile='diagnostic')
        self.profile.write_bytes(dataset_fixtures.encoded(dict(schema_version='r7-owner-selections-v0.2',
            cloud_root_id='synthetic-local-folder',research_policies={'selected-test':policy})))
        return config

    def configure(self):
        return self.call(['configure-research','--config',str(self.config_path),'--selection-profile',str(self.profile)])

    def test_first_run_cloud_root_is_explicit_disjoint_and_never_connected(self):
        config = self.initialize()
        self.assertEqual(config.cloud_root, self.cloud)
        self.assertFalse(self.cloud.exists()); self.assertFalse(self.data.exists())
        self.assertTrue(config.diagnostic_only); self.assertFalse(config.paper_runtime_enabled)

    def test_overlapping_cloud_root_never_publishes_profile_or_initializes_database(self):
        with self.assertRaises((ConfigError, ValueError)):
            cli.main(['init-profile','--config',str(self.config_path),'--data-root',str(self.data),
                      '--cloud-root',str(self.data/'nested'),'--instance-id','overlap'])
        self.assertFalse(self.config_path.exists()); self.assertFalse(self.data.exists())

    def test_config_inside_or_equal_to_cloud_root_is_rejected_before_any_write(self):
        for config_path in (self.cloud/'nested'/'config.json',self.cloud):
            with self.subTest(config_path=config_path),self.assertRaises(ValueError):
                cli.main(['init-profile','--config',str(config_path),'--data-root',str(self.data),
                          '--cloud-root',str(self.cloud),'--instance-id','cloud-config-boundary'])
            self.assertFalse(self.cloud.exists());self.assertFalse(self.data.exists())

    def test_explicit_setup_is_immutable_idempotent_and_creates_no_owner_database(self):
        config=self.prepare(); result=self.configure()
        self.assertEqual(result['status'],'RESEARCH_CONFIGURED')
        self.assertEqual(result['policy_count'],1); self.assertEqual(result['cloud'],'LOCAL_STAGING_SELECTED')
        self.assertEqual(result['paper'],'NOT_STARTED'); self.assertFalse(config.database_path.exists())
        original=(self.data/'owner-selections.json').read_bytes()
        self.assertEqual(self.configure()['status'],'ALREADY_CONFIGURED')
        self.assertEqual((self.data/'owner-selections.json').read_bytes(),original)
        value=json.loads(self.profile.read_bytes());value['research_policies']['selected-test']['seed']=43
        self.profile.write_bytes(dataset_fixtures.encoded(value))
        with self.assertRaises(ValueError): self.configure()
        self.assertEqual((self.data/'owner-selections.json').read_bytes(),original)

    def test_cloud_borne_selection_unknown_authority_and_missing_local_inputs_are_rejected(self):
        config=self.prepare(); original=self.profile.read_bytes()
        cases=[dict(json.loads(original),qualified_release='PASS'),dict(json.loads(original),workflow_authorized=True)]
        for value in cases:
            self.profile.write_bytes(dataset_fixtures.encoded(value))
            with self.assertRaises(ValueError): self.configure()
        self.profile.write_bytes(original)
        cloud_profile=self.cloud/'selection.json';cloud_profile.write_bytes(original)
        with self.assertRaises(ValueError):
            cli.main(['configure-research','--config',str(self.config_path),'--selection-profile',str(cloud_profile)])
        (self.data/'risk.json').unlink()
        with self.assertRaises(ValueError): self.configure()
        self.assertFalse((self.data/'owner-selections.json').exists());self.assertFalse(config.database_path.exists())

    def test_each_running_owner_fences_configuration_without_changing_selection(self):
        config=self.prepare()
        for role in ('control','research','runtime','cloud'):
            with self.subTest(role=role), ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)):
                with self.assertRaises(ScopeBusy): self.configure()
            self.assertFalse((self.data/'owner-selections.json').exists())
        self.assertEqual(self.configure()['status'],'RESEARCH_CONFIGURED')

    def test_outside_profile_hardlinked_to_cloud_input_is_rejected_without_publication(self):
        config=self.prepare();cloud_profile=self.cloud/'selection.json'
        cloud_profile.write_bytes(self.profile.read_bytes())
        alias=self.root/'operator-hardlink.json';os.link(cloud_profile,alias)
        with self.assertRaises(ValueError):
            cli.main(['configure-research','--config',str(self.config_path),'--selection-profile',str(alias)])
        self.assertFalse((self.data/'owner-selections.json').exists());self.assertFalse(config.database_path.exists())

    def test_canonical_cloud_alias_is_rejected_before_opening_profile_bytes(self):
        config=self.prepare()
        from application.research import setup
        with patch.object(Path,'resolve',autospec=True,return_value=self.cloud/'selection.json'), \
                patch.object(setup,'load_config',return_value=config), \
                patch.object(setup,'_windows_read',return_value=self.profile.read_bytes()) as reader:
            with self.assertRaises(ValueError): setup.configure_research(self.config_path,self.profile)
        reader.assert_not_called()
        self.assertFalse((self.data/'owner-selections.json').exists())

    def flow(self, outcome):
        config=self.prepare(outcome);self.configure()
        # The normal protected enrollment command is exercised with synthetic
        # hidden terminal input. Native interactive enrollment remains separate.
        secret='synthetic-source-setup-password-2026'
        with patch('sys.stdin.isatty',return_value=True),patch('getpass.getpass',side_effect=[secret,secret]):
            self.call(['enroll-owner','--config',str(self.config_path),'--username','fixture-owner'])
        assets=self.root/'ui';(assets/'assets').mkdir(parents=True)
        (assets/'index.html').write_text('SOURCE_FLOW_FIXTURE',encoding='utf-8')
        entry=importlib.import_module('application.entrypoints')
        app=entry.create_local_app(config,asset_root=assets)
        from fastapi.testclient import TestClient
        with TestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000)) as client:
            login=client.post('/api/v1/auth/login',json=dict(username='fixture-owner',password=secret,
                command_id='public-flow-login',expected_revision=0),headers={'Origin':'http://127.0.0.1:8765'})
            self.assertEqual(login.status_code,200,login.text)
            headers={'Origin':'http://127.0.0.1:8765','x-r7-csrf':login.json()['csrf_token']}
            scan=client.post('/api/v1/research/scan',json=dict(command_id='public-flow-scan',expected_revision=0),headers=headers)
            self.assertEqual(scan.status_code,200,scan.text)
            submission=client.get('/api/v1/submissions/public-flow-input').json()['data']
            enqueue=client.post('/api/v1/research/runs',json=dict(command_id='public-flow-enqueue',expected_revision=submission['revision'],
                submission_id='public-flow-input',policy_id='selected-test'),headers=headers)
            self.assertEqual(enqueue.status_code,202,enqueue.text)
            job=enqueue.json()['effect_ref'].removeprefix('research-job:')
            result=self.call(['research-worker','--config',str(self.config_path),'--once'])
            self.assertEqual(result['status'],'JOB_FINISHED');self.assertTrue(result['tree_reaped'])
            self.assertNotEqual(result['parent_pid'],result['child_pid'])
            actual=client.get('/api/v1/research/runs/'+job).json()['data']['payload']
            strategies=client.get('/api/v1/strategies').json()['data']['items']
            return actual,strategies[0]['current_lifecycle_state']

    def test_public_setup_login_scan_and_independent_worker_produce_actual_candidate(self):
        actual,lifecycle=self.flow('CANDIDATE')
        self.assertEqual(lifecycle,'CANDIDATE');self.assertEqual(actual['evidence']['sealed_oos'],'PASS')

    def test_actual_oos_losses_produce_rejection_through_normal_entry(self):
        actual,lifecycle=self.flow('REJECTED')
        self.assertEqual(lifecycle,'REJECTED');self.assertEqual(actual['evidence']['sealed_oos'],'FAIL')

    def test_actual_insufficient_oos_samples_never_become_candidate(self):
        actual,lifecycle=self.flow('INSUFFICIENT')
        self.assertEqual(lifecycle,'BACKTESTING');self.assertEqual(actual['state'],'COMPLETE')
        self.assertEqual(actual['outcome']['status'],'BLOCKED')
        self.assertEqual(actual['evidence']['status'],'BLOCKED')
        self.assertEqual(actual['evidence']['sealed_oos'],'BLOCKED')
