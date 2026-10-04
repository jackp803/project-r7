"""Server-selected native intake/research wiring uses actual existing owners."""
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.config import ProductConfig
from registry import StrategyIdentity
from strategy.v02.capabilities import build_capability_snapshot
from tests.application import cloud_fixtures, dataset_fixtures, test_research_robustness
from tests.application import test_product_assessment_binding
from tests.validation import robustness_fixtures


class LocalOwnerCompositionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 本機 owner 整合 ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root, self.cloud = self.base / '本機', self.base / '同步暫存'
        self.root.mkdir()
        self.cloud.mkdir()
        self.config = ProductConfig('r7-product-config-v0.2', 'owner-composition-fixture', self.root,
                                    self.cloud, self.root / 'canonical.sqlite3')
        self.clock = lambda: datetime(2026, 10, 4, tzinfo=timezone.utc)
        self.selection = self.root / 'owner-selections.json'

    def compose(self):
        module = importlib.import_module('application.local_owners')
        return module.LocalOwners(self.config, namespace='FIXTURE', clock=self.clock, worker_id='fixture-worker')

    def configured(self):
        test_research_robustness.selected(self.root)
        (self.root / 'risk.json').write_bytes(dataset_fixtures.encoded(test_product_assessment_binding.risk_fixture()))
        (self.cloud / '.r7-root.json').write_bytes(dataset_fixtures.encoded({'root_id': 'fixture-cloud-root'}))
        folder, manifest, definition = cloud_fixtures.package(self.cloud, submission='native-owner-fixture',
            version='0.2', definition=robustness_fixtures.subject())
        manifest['capability_snapshot_hash'] = build_capability_snapshot().snapshot_hash
        (folder / 'manifest.json').write_bytes(dataset_fixtures.encoded(manifest))
        policy = dict(dataset_ref='dataset.json', split_policy_ref='split.json', cost_policy_ref='cost.json',
            research_policy_ref='research.json', robustness_policy_ref='robustness.json', risk_policy_ref='risk.json',
            family_id='fixture-family', seed=42, requested_dataset_profile='fixture-data',
            requested_validation_profile='diagnostic', requested_robustness_profile='diagnostic')
        self.selection.write_bytes(dataset_fixtures.encoded(dict(schema_version='r7-owner-selections-v0.2',
            cloud_root_id='fixture-cloud-root', research_policies={'selected-fixture': policy})))
        return self.compose()

    def test_absent_local_selection_leaves_research_cloud_and_runtime_unconfigured(self):
        owners = self.compose()
        self.assertIsNone(owners.queue)
        self.assertIsNone(owners.inbox_factory)
        services = owners.control_services()
        health = services.view('health')
        self.assertEqual(health['storage'], 'E6_AND_CONTROL_STORES_AVAILABLE')
        self.assertEqual(health['research'], 'NOT_CONFIGURED')
        self.assertEqual(health['runtime'], 'NOT_CONFIGURED')
        self.assertFalse(health['live_authorized'])

    def test_hostile_selections_fail_before_initializing_canonical_database(self):
        examples = [
            dict(schema_version='unsupported', cloud_root_id=None, research_policies={}),
            dict(schema_version='r7-owner-selections-v0.2', cloud_root_id=None, research_policies={}, executable='forbidden'),
            dict(schema_version='r7-owner-selections-v0.2', cloud_root_id=None, research_policies={'x': {'dataset_ref': '../escape'}}),
        ]
        for payload in examples:
            self.selection.write_bytes(dataset_fixtures.encoded(payload))
            with self.subTest(payload=payload), self.assertRaises(ValueError): self.compose()
            self.assertFalse(self.config.database_path.exists())
        self.selection.write_bytes(b'{"schema_version":"a","schema_version":"b"}')
        with self.assertRaises(ValueError): self.compose()
        self.assertFalse(self.config.database_path.exists())

    def test_selected_scan_enqueue_and_actual_owner_execution_preserve_canonical_flow(self):
        owners = self.configured()
        with owners.inbox_factory() as inbox:
            summary = inbox.scan_once(self.clock())
        self.assertEqual(summary.accepted, 1)
        with owners.registry_factory() as e6:
            definition = robustness_fixtures.subject()
            identity = StrategyIdentity(definition['strategy_id'], definition['strategy_version'])
            self.assertEqual(e6.get_strategy(identity).current_lifecycle_state, 'DRAFT')
        revision = owners.queue.selected_submission_revision('native-owner-fixture', 'selected-fixture')
        queued = owners.queue.enqueue('native-owner-fixture', 'selected-fixture', 'native-enqueue', revision, actor='fixture-owner')
        claim = owners.queue.claim_next()
        self.assertEqual(claim.run_id, queued['run_id'])
        result = owners.queue.step(claim.run_id, claim.generation)
        self.assertEqual(result['state'], 'COMPLETE')
        self.assertEqual(result['outcome']['strategy_lifecycle'], 'CANDIDATE')
        evidence = owners.queue.evidence_view(claim.run_id)
        self.assertEqual(evidence['sealed_oos'], 'PASS')
        self.assertEqual(owners.control_services().view('health')['runtime'], 'NOT_CONFIGURED')

    def test_policy_drift_blocks_queued_work_instead_of_reinterpreting_selection(self):
        owners = self.configured()
        with owners.inbox_factory() as inbox: inbox.scan_once(self.clock())
        revision = owners.queue.selected_submission_revision('native-owner-fixture', 'selected-fixture')
        owners.queue.enqueue('native-owner-fixture', 'selected-fixture', 'native-enqueue', revision, actor='fixture-owner')
        claim = owners.queue.claim_next()
        settings = json.loads(self.selection.read_bytes())
        settings['research_policies']['selected-fixture']['seed'] = 43
        self.selection.write_bytes(dataset_fixtures.encoded(settings))
        current = self.compose()
        result = current.queue.step(claim.run_id, claim.generation)
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertIn('QUEUED_SELECTION_CHANGED', result['reason_codes'])
