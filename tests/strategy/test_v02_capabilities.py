import copy
import importlib.util
import unittest

from tests.strategy.v02_fixtures import definition_v02


class CapabilityTests(unittest.TestCase):
    def test_e1_aggregation_or_e5_exit_semantics_change_requires_fresh_capability_binding(self):
        api=self.api()
        from pathlib import Path
        from unittest.mock import patch
        source=Path(api.__file__).resolve().parents[2]
        initial=api.build_capability_snapshot().snapshot_hash
        actual_read=Path.read_bytes
        for relative in ('market_data/aggregation.py','position/exit_requests.py'):
            target=source/relative
            with self.subTest(module=relative):
                def changed_read(path):
                    raw=actual_read(path)
                    return raw+b'\n# owner semantics changed\n' if path.resolve()==target.resolve() else raw
                with patch.object(Path,'read_bytes',changed_read):
                    changed=api.build_capability_snapshot().snapshot_hash
                self.assertNotEqual(initial,changed)

    def test_checkout_line_endings_do_not_create_different_implementation_identity(self):
        api=self.api()
        from pathlib import Path
        from unittest.mock import patch
        initial=api.build_capability_snapshot().snapshot_hash
        actual_read=Path.read_bytes
        def crlf_read(path):
            return actual_read(path).replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        with patch.object(Path,'read_bytes',crlf_read):
            changed=api.build_capability_snapshot().snapshot_hash
        self.assertEqual(initial,changed)

    def test_numerical_implementation_change_invalidates_exact_capability_identity(self):
        api=self.api()
        from pathlib import Path
        from unittest.mock import patch
        target=Path(api.__file__).resolve().parents[2]/'indicators/v02/bands.py'
        self.assertTrue(target.is_file())
        initial=api.build_capability_snapshot().snapshot_hash
        actual_read=Path.read_bytes
        def changed_read(path):
            raw=actual_read(path)
            return raw+b'\n# numerical implementation changed\n' if path.resolve()==target.resolve() else raw
        with patch.object(Path,'read_bytes',changed_read):
            changed=api.build_capability_snapshot().snapshot_hash
        self.assertNotEqual(initial,changed)

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

