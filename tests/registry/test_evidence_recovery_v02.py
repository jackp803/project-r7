import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from registry import EvidenceGateError
from storage.platform import open_sqlite_platform
from tests.registry.test_validation_lifecycle import strategy_payload,backtest_payload,validation_decision_payload

class EvidenceRecoveryTests(unittest.TestCase):
    def metadata(self):
        return dict(verification_status='PASS',verification_kind='LOCAL_EXECUTION',source_revision='fixture-source',
                    environment='fixture-local',command='fixture-command',result_ref='fixture:original-run')
    def test_same_upstream_evidence_is_recovered_after_restart_with_original_identity(self):
        with TemporaryDirectory() as root:
            path=Path(root)/'registry.sqlite'
            with open_sqlite_platform(path) as service:
                service.intake(strategy_payload(),source_actor='fixture')
                original=service.record_backtest_result(backtest_payload(),**self.metadata())
                decision=service.record_validation_decision(validation_decision_payload('bt-1'),backtest_evidence_id=original.evidence_id,**self.metadata())
            with open_sqlite_platform(path) as resumed:
                self.assertEqual(original,resumed.record_backtest_result(backtest_payload(),**self.metadata()))
                self.assertEqual(decision,resumed.record_validation_decision(validation_decision_payload('bt-1'),backtest_evidence_id=original.evidence_id,**self.metadata()))
    def test_changed_same_upstream_payload_source_and_verification_are_immutable_conflicts(self):
        with TemporaryDirectory() as root,open_sqlite_platform(Path(root)/'registry.sqlite') as service:
            service.intake(strategy_payload(),source_actor='fixture')
            original=service.record_backtest_result(backtest_payload(),**self.metadata())
            changed=copy.deepcopy(backtest_payload()); changed['net_pnl']='2'; changed['expectancy']='2'
            for payload,metadata in ((changed,self.metadata()),(backtest_payload(),dict(self.metadata(),source_revision='new-source')),
                                     (backtest_payload(),dict(self.metadata(),verification_status='NOT_RUN',verification_kind='NOT_RUN'))):
                with self.subTest(metadata=metadata),self.assertRaises(EvidenceGateError):
                    service.record_backtest_result(payload,**metadata)
            self.assertEqual(original,service.record_backtest_result(backtest_payload(),**self.metadata()))
    def test_competing_writers_return_one_original_evidence_identity(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        with TemporaryDirectory() as root:
            path=Path(root)/'registry.sqlite'
            with open_sqlite_platform(path) as service: service.intake(strategy_payload(),source_actor='fixture')
            barrier=Barrier(2)
            def record():
                with open_sqlite_platform(path) as service:
                    barrier.wait(timeout=5)
                    return service.record_backtest_result(backtest_payload(),**self.metadata())
            with ThreadPoolExecutor(max_workers=2) as pool:
                one,two=list(pool.map(lambda _:record(),range(2)))
            self.assertEqual(one,two)
