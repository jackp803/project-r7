"""Read-only source regression probe while exact-clean qualification runs."""
import sys,json,unittest
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
REPO=Path(__file__).resolve().parent.parent/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(REPO),str(REPO/'src')]
from tests.application.test_submission_validity_intake import SubmissionValidityIntakeTests,NOW,z

class ManifestSwapProbe(SubmissionValidityIntakeTests):
    def test_snapshot_manifest_replacement_cannot_use_old_validity(self):
        with self.fixture() as (inbox,ledger,e6,folder):
            snapshot=inbox.transport.snapshot
            def replace(descriptor,root):
                path=folder/'manifest.json';manifest=json.loads(path.read_bytes())
                manifest['validity']={'from':z(NOW-timedelta(hours=2)),'until':z(NOW-timedelta(hours=1))}
                path.write_text(json.dumps(manifest),encoding='utf-8')
                return snapshot(descriptor,root)
            with patch.object(inbox.transport,'snapshot',side_effect=replace):
                result=inbox.scan_once(NOW).results[0]
            self.assertEqual(result.state,'INCOMPLETE_SYNC')
            self.assertEqual(result.reason_codes,('MANIFEST_CHANGED_DURING_SNAPSHOT',))
            self.assertIsNone(ledger.get_submission('tactical'))
            self.assertIsNone(ledger.accepted_receipt('tactical'))
            self.assertEqual(sum(e6.lifecycle_counts().values()),0)
            self.assertEqual(ledger.pending_outbox(10),())
            self.assertEqual(inbox.scan_once(NOW+timedelta(seconds=6)).results[0].state,'EXPIRED')

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([ManifestSwapProbe('test_snapshot_manifest_replacement_cannot_use_old_validity')]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
