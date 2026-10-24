"""Normal backup/restore of actual encoded funding-pending source owners.

Source/native/clock boundaries are explicit controlled fixtures; no native PASS.
"""
from contextlib import ExitStack
from datetime import datetime,timedelta
import unittest
from unittest.mock import patch

from application.config import load_config
from application.platform.product_backup import create_product_backup,verify_product_backup,restore_product_backup
from application.platform.restoration import require_valid_restoration
from storage.paper_process import open_paper_process_journal
from tests.product import test_paper_encoded_checkpoint_consumers as encoded


class RecordedPaperBackupTests(unittest.TestCase):
    def test_normal_full_product_restore_preserves_exact_encoded_pending_facts_and_imports_no_permission(self):
        case=encoded.EncodedRecordedFundingRegressionTests();self.addCleanup(case.doCleanups)
        # Close the actual service/supervisor before the original backup entry,
        # retaining helper-owned source inputs until the final test cleanup.
        with ExitStack() as owners:
            case.enterContext=owners.enter_context
            case.close_pending(instance_id='encoded-recorded-backup-regression')
            original=case.service.process.management_snapshot(case.ref.run_id)
            self.assertIsNotNone(original.state['runtime']['pending_funding'])
            self.assertEqual(original.state['runtime']['closed_trades'],[])
            self.assertTrue(case.service.process.history_audit_ready(case.ref.run_id))
        destination=case.h.root/'actual-product-backup'
        create_product_backup(case.config,destination,timeout_seconds=30)
        verify_product_backup(case.config,destination,timeout_seconds=30)
        at=case.clock[0]+timedelta(seconds=1)
        class ControlledRestoreClock(datetime):
            @classmethod
            def now(cls,tz=None):return at.astimezone(tz) if tz is not None else at.replace(tzinfo=None)
        # The existing LOCAL source fixture runs ahead of actual wall time.
        # Restore uses its consistent clock; no stored timestamp/guard changes.
        with patch('application.platform.database_restore.datetime',ControlledRestoreClock):
            restore_product_backup(case.config,destination,case.h.root/'restored',timeout_seconds=30)
        restored=load_config(case.h.root/'restored/restored-product.json')
        self.assertEqual(require_valid_restoration(restored)['status'],'RESTORED_INHIBITED')
        self.assertIsNone(restored.cloud_root);self.assertFalse(restored.paper_runtime_enabled)
        with open_paper_process_journal(restored.database_path) as journal:
            actual=journal.audit_full(case.ref.run_id)
            self.assertEqual(actual.state_json,original.state_json)
            self.assertEqual(actual.binding_json,original.binding_json)
            self.assertEqual(actual.process_generation,original.process_generation+1)
            self.assertFalse(journal.history_audit_ready(case.ref.run_id))
            self.assertIsNotNone(actual.state['runtime']['pending_funding'])
            self.assertEqual(actual.state['runtime']['closed_trades'],[])
        with open_paper_process_journal(case.config.database_path) as source:
            self.assertEqual(source.management_snapshot(case.ref.run_id).process_generation,original.process_generation)


if __name__=='__main__':unittest.main()
