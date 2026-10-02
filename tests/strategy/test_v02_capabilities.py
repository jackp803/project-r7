import copy
import importlib.util
import unittest

from tests.strategy.v02_fixtures import definition_v02


class CapabilityTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('strategy.v02.capabilities'),
                             'Executable capability registry is missing')
        from strategy.v02 import capabilities
        return capabilities

    def test_recognized_indicator_does_not_claim_verified_execution_or_provider(self):
        snapshot=self.api().build_capability_snapshot()
        ema=next(row for row in snapshot.as_dict()['capabilities'] if row['capability_id']=='indicator:EMA')
        self.assertTrue(ema['validator_available'])
        self.assertFalse(ema['IMPLEMENTED'])
        self.assertFalse(ema['VERIFIED_REFERENCE'])
        self.assertFalse(ema['PAPER_AVAILABLE'])
        self.assertFalse(ema['LIVE_PROVIDER_AVAILABLE'])
        report=self.api().check_compatibility(definition_v02(),snapshot)
        self.assertEqual('BLOCKED',report.status)
        self.assertIn('NOT_IMPLEMENTED',[gap.reason for gap in report.gaps])

    def test_snapshot_hash_is_deterministic_and_snapshot_cannot_be_mutated(self):
        api=self.api()
        snapshot=api.build_capability_snapshot()
        initial=snapshot.as_dict()
        self.assertEqual(snapshot.snapshot_hash,api.build_capability_snapshot().snapshot_hash)
        initial['capabilities'][0]['IMPLEMENTED']=True
        self.assertNotEqual(initial,snapshot.as_dict())
        self.assertRegex(snapshot.snapshot_hash,r'^sha256:[0-9a-f]{64}$')

    def test_unknown_version_gap_names_exact_source_and_available_version(self):
        api=self.api()
        value=definition_v02()
        value['rules']['features']['trend']['semantic_version']='r7-ema-v99'
        report=api.check_compatibility(value,api.build_capability_snapshot())
        gap=next(gap for gap in report.gaps if gap.reason=='UNSUPPORTED_VERSION')
        self.assertEqual('r7-ema-v99',gap.requested_version)
        self.assertEqual('r7-ema-v1',gap.available_version)
        self.assertEqual('/rules/features/trend',gap.source_location)
        self.assertTrue(gap.reevaluation_conditions)

    def test_changed_snapshot_hash_does_not_transfer_compatibility(self):
        api=self.api()
        report=api.check_compatibility(definition_v02(),api.build_capability_snapshot(),
                                       required_snapshot_hash='sha256:'+'0'*64)
        self.assertEqual('BLOCKED',report.status)
        self.assertEqual('CAPABILITY_SNAPSHOT_MISMATCH',report.gaps[0].reason)

