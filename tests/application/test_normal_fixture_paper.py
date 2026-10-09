"""Actual public fixture selection and PaperStart; no injected owner factories."""
import json
import sqlite3
from contextlib import closing
import unittest
from unittest.mock import patch

from application import cli
from application.config import load_config
from application.platform.scope_lock import ProcessScopeLock, ScopeBusy, operational_lock_root
from registry import EvidenceGateError
from tests.application import test_fixture_recipe_flow as recipe
from tests.application import test_research_setup_flow as normal


class NormalFixturePaperTests(unittest.TestCase):
    setUp = recipe.FixtureRecipeFlowTests.setUp
    call = recipe.FixtureRecipeFlowTests.call
    initialize = recipe.FixtureRecipeFlowTests.initialize
    generate = recipe.FixtureRecipeFlowTests.generate
    prepare = recipe.FixtureRecipeFlowTests.prepare
    configure = recipe.FixtureRecipeFlowTests.configure
    app = recipe.FixtureRecipeFlowTests.app
    flow = recipe.FixtureRecipeFlowTests.flow

    def configure_paper(self):
        return self.call(['configure-paper','--config',str(self.config_path),
            '--selection-profile',str(self.data/'fixture-inputs'/'paper-selection.json')])

    def test_ordinary_mode_has_no_fixture_paper_authority_or_side_effect(self):
        normal.ResearchSetupFlowTests.initialize(self)
        with self.assertRaises(ValueError):
            self.configure_paper()
        self.assertFalse(self.data.exists())

    def test_all_running_owners_fence_paper_selection(self):
        config, _ = self.prepare()
        self.configure()
        for role in ('control','research','runtime','cloud'):
            with self.subTest(role=role),ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)):
                with self.assertRaises(ScopeBusy):
                    self.configure_paper()
            self.assertFalse((self.data/'paper-owner-selections.json').exists())

    def test_operator_profile_cannot_supply_qualification_or_workflow_authority(self):
        self.prepare()
        path = self.data/'fixture-inputs'/'paper-selection.json'
        original = path.read_bytes()
        for field in ('qualified_release','workflow_authorized','approval','release_kind'):
            value = json.loads(original)
            value[field] = 'PASS'
            path.write_text(json.dumps(value),encoding='utf-8')
            with self.assertRaises(ValueError):
                self.configure_paper()
        self.assertFalse((self.data/'paper-owner-selections.json').exists())

    def test_normal_candidate_selects_paper_and_api_prepares_generation_zero(self):
        actual, lifecycle = self.flow('positive')
        self.assertEqual(lifecycle,'CANDIDATE')
        result = self.configure_paper()
        self.assertEqual(result['status'],'FIXTURE_PAPER_CONFIGURED')
        self.assertEqual(result['financial_authority'],'NONE')
        before = (self.data/'paper-owner-selections.json').read_bytes()
        self.assertEqual(self.configure_paper()['status'],'ALREADY_CONFIGURED')
        self.assertEqual((self.data/'paper-owner-selections.json').read_bytes(),before)
        config = load_config(self.config_path)
        from fastapi.testclient import TestClient
        with TestClient(self.app(config),base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000)) as client:
            login = client.post('/api/v1/auth/login',json=dict(username='fixture-owner',
                password='synthetic-source-recipe-password-2026',command_id='paper-login',expected_revision=0),
                headers={'Origin':'http://127.0.0.1:8765'})
            self.assertEqual(login.status_code,200,login.text)
            headers = {'Origin':'http://127.0.0.1:8765','x-r7-csrf':login.json()['csrf_token']}
            policies = client.get('/api/v1/policies').json()['data']['items']
            paper = [row for row in policies if row['kind']=='PAPER']
            self.assertEqual(len(paper),1)
            self.assertEqual(paper[0]['mode'],'ACCELERATED_FIXTURE')
            strategy = client.get('/api/v1/strategies').json()['data']['items'][0]
            start = client.post('/api/v1/paper/runs',json=dict(command_id='normal-paper-start',
                expected_revision=strategy['registry_revision'],strategy_id=strategy['identity']['strategy_id'],
                strategy_version=strategy['identity']['strategy_version'],policy_id=paper[0]['policy_id']),headers=headers)
            self.assertEqual(start.status_code,200,start.text)
            run = start.json()['effect_ref'].removeprefix('paper:')
            from storage.paper_process import open_paper_process_journal
            with open_paper_process_journal(config.database_path,require_existing=True) as journal:
                self.assertEqual(journal.recover(run).process_generation,0)
            payload = client.get('/api/v1/paper/runs/'+run).json()['data']['payload']
            self.assertEqual(payload['mode'],'ACCELERATED_FIXTURE')
            self.assertEqual(payload['runtime_status'],'NOT_STARTED')
            self.assertEqual(payload['closed_trades_count'],0)
            with closing(sqlite3.connect(self.data/'process-supervision.sqlite')) as supervision:
                self.assertEqual(supervision.execute("SELECT COUNT(*) FROM process_session_history WHERE role='runtime'").fetchone()[0],0)

    def selected_candidate(self):
        self.assertEqual(self.flow('positive')[1],'CANDIDATE')
        self.configure_paper()
        return load_config(self.config_path),self.data/'paper-owner-selections.json'

    def test_restarted_reader_must_match_all_selected_policy_bytes(self):
        config, path = self.selected_candidate()
        original = path.read_bytes()
        for field in ('simulation_policy','risk_policy','promotion_policy'):
            value = json.loads(original)
            if field=='simulation_policy': value['owner'][field]['quantity']='0.002'
            elif field=='risk_policy': value['owner'][field]['policy']['max_margin']='99'
            else: value['owner'][field]['max_drawdown_usdt']='20'
            path.write_text(json.dumps(value),encoding='utf-8')
            with self.subTest(field=field),self.assertRaises((ValueError,EvidenceGateError)):
                self.app(config)
        path.write_bytes(original)

    def test_restarted_reader_must_match_actual_selected_manifest_and_validity(self):
        config, path = self.selected_candidate()
        original = path.read_bytes()
        for field in ('submission_id','manifest_hash','submission_validity'):
            value = json.loads(original)
            if field=='submission_id': value[field]='other-synthetic-submission'
            elif field=='manifest_hash': value[field]='sha256:'+'f'*64
            else: value['owner'][field]=dict(intent_class='TACTICAL_STRATEGY',
                validity={'from':'2026-10-01T00:00:00Z','until':'2026-11-01T00:00:00Z'})
            path.write_text(json.dumps(value),encoding='utf-8')
            with self.subTest(field=field),self.assertRaises((ValueError,EvidenceGateError)):
                self.app(config)
        path.write_bytes(original)

    def test_composed_reader_revalidates_sealed_payload_before_start(self):
        config, path = self.selected_candidate()
        from application.local_owners import LocalOwners
        local = LocalOwners(config,namespace='FIXTURE')
        local.control_services()
        record = json.loads(path.read_bytes())
        _, package = local.resolver.package(record['submission_id'])
        payload = package.snapshot.payload_paths['strategy_definition']
        original = payload.read_bytes()
        payload.write_bytes(original+b' ')
        with self.assertRaises(EvidenceGateError):
            local.paper_owners.current_release()
        payload.write_bytes(original)
        self.assertEqual(local.paper_owners.current_release().namespace,'FIXTURE')
