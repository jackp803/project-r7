from contextlib import ExitStack, contextmanager
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

from application.cloud.synced_folder import SyncedFolderCloudTransport
from application.config import ProductConfig
from application.intake.ledger import IntakeLedger
from application.intake.service import StrategyInboxService
from application.research.service import ResearchService
from application.research.queue import ResearchQueue
from storage.platform import open_sqlite_platform
from strategy.v02.capabilities import build_capability_snapshot
from tests.application.cloud_fixtures import package
from tests.application.dataset_fixtures import encoded
from tests.application.test_product_assessment_binding import risk_fixture
from tests.application.test_research_robustness import selected
from tests.validation.robustness_fixtures import subject
from tests.product.test_api_authority import APIFixture


class APIOwnerServicesTests(APIFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('application.control_api.owner_services'),
                             'HTTP must wire the actual local owner services')
        from application.control_api.owner_services import OwnerControlServices
        from application.research.selection import ResearchRequestResolver
        from application.control_api.app import create_app
        selected(self.root); (self.root/'risk.json').write_bytes(encoded(risk_fixture()))
        cloud_temp=TemporaryDirectory(); self.addCleanup(cloud_temp.cleanup); self.cloud=Path(cloud_temp.name)
        (self.cloud/'.r7-root.json').write_bytes(encoded({'root_id':'fixture-cloud-root'}))
        folder, manifest, definition = package(self.cloud, submission='fixture-product', version='0.2', definition=subject())
        manifest['capability_snapshot_hash'] = build_capability_snapshot().snapshot_hash
        (folder/'manifest.json').write_bytes(encoded(manifest))
        self.ledger_path = self.root/'intake.sqlite'
        self.snapshots = self.root/'snapshots'
        self.registry_factory = lambda: open_sqlite_platform(self.config.database_path, research_namespace='FIXTURE')
        self.intake_factory = lambda: IntakeLedger(self.ledger_path, instance_id=self.config.product_instance_id)
        @contextmanager
        def inbox():
            with self.intake_factory() as ledger, self.registry_factory() as e6:
                yield StrategyInboxService(SyncedFolderCloudTransport(self.cloud,expected_root_id='fixture-cloud-root'), ledger, e6,
                    snapshot_root=self.snapshots, owner_id='fixture-scan-owner', capability_snapshot_hash=build_capability_snapshot().snapshot_hash)
        self.inbox_factory = inbox
        self.policy = dict(dataset_ref='dataset.json', split_policy_ref='split.json', cost_policy_ref='cost.json',
            research_policy_ref='research.json', robustness_policy_ref='robustness.json', risk_policy_ref='risk.json',
            family_id='fixture-family', seed=42, requested_dataset_profile='fixture-data',
            requested_validation_profile='diagnostic', requested_robustness_profile='diagnostic')
        resolver = ResearchRequestResolver(self.root, snapshot_root=self.snapshots, intake_factory=self.intake_factory,
            registry_factory=self.registry_factory, policies={'selected-fixture': self.policy})
        self.queue = ResearchQueue(self.root/'queue.sqlite', namespace='FIXTURE', owner_id='fixture-worker',
            resolve_request=resolver.resolve, service_factory=lambda: ResearchService(local_root=self.root, database_path=self.root/'research.sqlite',
                registry_path=self.config.database_path, namespace='FIXTURE', owner_id='fixture-worker'), clock=lambda:self.clock[0])
        self.owners = OwnerControlServices(self.config, namespace='FIXTURE', clock=lambda:self.clock[0],
            registry_factory=self.registry_factory, intake_factory=self.intake_factory, inbox_factory=inbox,
            research_queue=self.queue, research_resolver=resolver)
        self.app = create_app(self.config, auth=self.auth, commands=self.ledger, services=self.owners)
        from fastapi.testclient import TestClient
        self.client.close()
        self.client = TestClient(self.app, base_url='http://127.0.0.1:8765', client=('127.0.0.1',42000), raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.login()

    def scan(self):
        response = self.post('/api/v1/research/scan', dict(command_id='scan-one', expected_revision=0))
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def enqueue(self):
        self.scan()
        submission = self.client.get('/api/v1/submissions/fixture-product').json()['data']
        response = self.post('/api/v1/research/runs', dict(command_id='enqueue-one', expected_revision=submission['revision'],
            submission_id='fixture-product', policy_id='selected-fixture'))
        self.assertEqual(response.status_code, 202, response.text)
        return response

    def test_actual_scan_inventory_and_identical_retry_use_e6_and_sealed_intake(self):
        response = self.scan(); retry = self.post('/api/v1/research/scan', dict(command_id='scan-one', expected_revision=0))
        self.assertEqual(response.json(), retry.json())
        submissions = self.client.get('/api/v1/submissions').json()['data']
        self.assertEqual(submissions['items'][0]['state'], 'INTAKE_ACCEPTED')
        strategies = self.client.get('/api/v1/strategies').json()['data']
        self.assertEqual(strategies['items'][0]['current_lifecycle_state'], 'DRAFT')
        self.assertEqual(strategies['items'][0]['content_hash'], subject()['content_hash'])

    def test_scan_revision_survives_reload_for_real_optimistic_ui_commands(self):
        self.assertEqual(self.client.get('/api/v1/overview').json()['data'].get('scan_revision'),0)
        self.scan()
        self.assertEqual(self.client.get('/api/v1/overview').json()['data'].get('scan_revision'),1)
        response=self.post('/api/v1/research/scan',dict(command_id='scan-after-reload',expected_revision=1))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['resource_revision'],2)

    def test_ui_reads_canonical_rule_timeframe_hold_and_verified_author_manifest(self):
        self.scan()
        detail=self.client.get('/api/v1/strategies/'+subject()['strategy_id']+'/'+subject()['strategy_version']).json()['data']['payload']
        self.assertEqual(detail['evaluation_timeframe'],subject()['rules']['evaluation_timeframe'])
        self.assertEqual(detail['max_hold_seconds'],subject()['rules']['exit_policy']['max_hold_seconds'])
        self.assertEqual(detail.get('author_metadata',{}).get('submission_id'),'fixture-product')
        self.assertEqual(detail['author_metadata']['manifest']['research_hypothesis'],'測試宣告式策略')
        submission=self.client.get('/api/v1/submissions/fixture-product').json()['data']['payload']
        self.assertEqual(submission.get('author_manifest',{}).get('research_hypothesis'),'測試宣告式策略')
        self.assertEqual(submission['author_manifest']['intent_class'],'EVERGREEN_STRATEGY')
        self.assertEqual(submission['author_manifest']['validity'],{'from':None,'until':None})

    def test_actual_async_research_reaches_candidate_and_api_reports_owner_lineage(self):
        response = self.enqueue()
        self.assertEqual(response.json()['status'], 'QUEUED')
        self.assertFalse((self.root/'research.sqlite').exists())
        job_id = response.json()['effect_ref'].removeprefix('research-job:')
        self.assertEqual(self.client.get('/api/v1/research/runs/'+job_id).json()['data']['payload']['state'], 'QUEUED')
        claim = self.queue.claim_next(); self.queue.step(claim.run_id,claim.generation)
        view = self.client.get('/api/v1/research/runs/'+job_id).json()['data']['payload']
        self.assertEqual(view['outcome']['strategy_lifecycle'], 'CANDIDATE')
        self.assertEqual(view['owner_run_id'], view['outcome']['run_id'])
        self.assertIn('evidence',view,'HTTP needs actual owner metrics/cost/lineage summaries')
        self.assertGreater(view['evidence']['backtest']['total_trades'],0)
        self.assertEqual(view['evidence']['provenance']['provider_requests'],0)
        strategy = self.client.get('/api/v1/strategies/'+subject()['strategy_id']+'/'+subject()['strategy_version']).json()['data']
        self.assertEqual(strategy['payload']['current_lifecycle_state'], 'CANDIDATE')
        self.assertEqual(self.client.get('/api/v1/overview').json()['data']['lifecycle_counts'], {'CANDIDATE':1})

    def test_configured_dataset_page_reads_actual_registered_catalog_without_claiming_decode(self):
        response=self.client.get('/api/v1/datasets')
        self.assertEqual(response.status_code,200,response.text)
        page=response.json()['data']
        self.assertEqual(len(page['items']),1)
        self.assertEqual(page['items'][0]['namespace'],'FIXTURE')
        self.assertEqual(page['items'][0]['verification_scope'],'MANIFEST_ONLY')
        self.assertEqual(page['items'][0]['information_cutoff'],json.loads((self.root/'dataset.json').read_bytes())['information_cutoff'])

    def test_actual_cancel_retains_queued_inputs_and_never_creates_research_evidence(self):
        response = self.enqueue(); job_id = response.json()['effect_ref'].removeprefix('research-job:')
        body = dict(command_id='cancel-one', expected_revision=0)
        canceled = self.post('/api/v1/research/runs/'+job_id+'/cancel', body)
        self.assertEqual(canceled.status_code, 200, canceled.text)
        self.assertEqual(canceled.json(), self.post('/api/v1/research/runs/'+job_id+'/cancel',body).json())
        self.assertEqual(self.queue.get(job_id)['state'], 'CANCELED')
        self.assertIsNone(self.queue.claim_next())
        self.assertFalse((self.root/'research.sqlite').exists())

    def test_changed_sealed_snapshot_cannot_enter_queue(self):
        self.scan()
        path = next(self.snapshots.glob('fixture-product-*'))/'strategy.json'
        path.write_text('{}', encoding='utf-8')
        response = self.post('/api/v1/research/runs', dict(command_id='enqueue-one', expected_revision=1,
            submission_id='fixture-product', policy_id='selected-fixture'))
        self.assertNotEqual(response.status_code,202)
        self.assertEqual(self.queue.list(), [])


if __name__ == '__main__': unittest.main()
