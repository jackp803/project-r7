"""Actual LOCAL owners: historical eligibility gates entry, never protection."""
import time
import unittest
from unittest.mock import patch

from application.paper.assessment import assess_forward
from storage.paper_history_worker import OwnedPaperHistoryAudit
from storage.paper_process import PaperProcessJournal
from tests.product import test_paper_encoded_checkpoint_consumers as encoded
from tests.product import test_paper_recorded_funding as fixture


class PaperHistoryGateTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.PaperRecordedFundingTests();self.addCleanup(self.case.doCleanups)
        original=PaperProcessJournal.create_run
        with patch.object(PaperProcessJournal,'create_run',new=encoded.encoded_create(original)):
            self.case.prepare()
        self.journal=self.case.service.process;self.run=self.case.ref.run_id

    def verify_history(self):
        worker=self.journal._background_history or OwnedPaperHistoryAudit(self.journal)
        worker.start(self.run);deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            progress=worker.poll(self.run)
            if self.journal.history_audit_ready(self.run):return
            if progress.status=='HISTORY_AUDIT_FAILED':self.fail('Actual owning history audit failed')
            time.sleep(.02)
        self.fail('Actual local audit did not finish')

    def test_unaudited_current_snapshot_cannot_submit_entry_or_credit_healthy_forward(self):
        result=self.case.runtime.on_market_event(self.case.event(0,bars=True))
        self.assertEqual(result.status,'BLOCKED')
        self.assertIn('HISTORY_AUDIT_REQUIRED',result.reason_codes)
        self.case.runtime.on_market_event(self.case.event(1))
        current=self.journal.recover_current(self.run)
        self.assertEqual(current.state['broker']['payload']['submissions'],[])
        self.assertFalse(current.state['runtime']['forward']['last_healthy'])
        assessment=assess_forward(self.case.runtime,self.case.service.promotion).as_dict()
        self.assertIn('HISTORY_AUDIT_REQUIRED',assessment['reason_codes'])

    def test_verified_history_uses_bounded_current_reads_and_retains_actual_entry_and_protection(self):
        self.verify_history()
        with patch.object(self.journal,'recover',side_effect=AssertionError('Hot owner scanned complete old history')):
            self.assertEqual(self.case.runtime.on_market_event(self.case.event(0,bars=True)).status,'ACKNOWLEDGED')
            self.assertEqual(self.case.runtime.on_market_event(self.case.event(1)).status,'PROTECTED')
            self.case.runtime.on_deadline(self.case.clock[0])
        self.assertTrue(self.journal.history_audit_ready(self.run))

    def test_unknown_history_mutation_inhibits_credit_but_existing_protection_exit_and_pending_continue(self):
        self.journal._db.execute('CREATE TABLE controlled_counter(value INTEGER)');self.journal._db.commit()
        self.verify_history()
        self.assertEqual(self.case.runtime.on_market_event(self.case.event(0,bars=True)).status,'ACKNOWLEDGED')
        self.assertEqual(self.case.runtime.on_market_event(self.case.event(1)).status,'PROTECTED')
        self.journal._db.execute('INSERT INTO controlled_counter VALUES(1)');self.journal._db.commit()
        self.assertFalse(self.journal.history_audit_ready(self.run))
        self.case.latest[0]=None
        self.assertEqual(self.case.runtime.on_market_event(self.case.event(2,price='60020')).status,'EXIT_REQUESTED')
        self.assertEqual(self.case.runtime.on_market_event(self.case.event(3,price='60020')).status,'FUNDING_PENDING')
        state=self.journal.recover_current(self.run).state['runtime']
        self.assertFalse(state['forward']['last_healthy'])
        self.assertEqual(state['closed_trades'],[])

    def test_normal_service_drives_owned_audit_after_management_and_control_remains_last_known(self):
        from application.control_api.paper_ports import PaperReadControlPort
        from storage.paper_process import open_paper_process_journal
        from storage.runtime import open_paper_runtime_journal
        self.assertTrue(callable(getattr(self.case.service,'history_audit_after_protection',None)),
            'Normal owner has no protective-first audit scheduling seam')
        self.case.runtime.on_market_event(self.case.event(0,bars=True))
        deadline=time.monotonic()+20
        while time.monotonic()<deadline and not self.journal.history_audit_ready(self.run):
            self.case.service.history_audit_after_protection((self.run,));time.sleep(.02)
        self.assertTrue(self.journal.history_audit_ready(self.run))
        self.assertEqual(self.case.runtime.on_market_event(self.case.event(1)).status,'ACKNOWLEDGED')
        reader=PaperReadControlPort(namespace='LOCAL_RESEARCH',
            process_factory=lambda:open_paper_process_journal(self.case.config.database_path,require_existing=True),
            canonical_factory=lambda:open_paper_runtime_journal(self.case.config.database_path,require_existing=True),
            clock=lambda:self.case.clock[0])
        view=reader.view(self.run)
        self.assertEqual(view['status'],'LAST_KNOWN_OWNER_FACTS')
        self.assertEqual(view['payload']['history']['scope'],'LAST_KNOWN_DIAGNOSTIC_ONLY')
        self.assertEqual(view['payload']['history']['last_observation']['status'],'HISTORY_VERIFIED_IN_CURRENT_INSTANCE')
        self.assertEqual(view['payload']['history']['current_admission'],'OWNER_INSTANCE_REVALIDATION_REQUIRED')

    def test_successor_cannot_inherit_saved_verified_diagnostic_or_fill_prior_entry(self):
        self.verify_history()
        self.assertEqual(self.case.runtime.on_market_event(self.case.event(0,bars=True)).status,'ACKNOWLEDGED')
        saved=self.journal.recover_current(self.run).state['runtime']['history_audit_observation']
        self.assertEqual(saved['status'],'HISTORY_VERIFIED_IN_CURRENT_INSTANCE')
        successor=self.enterContext(self.case.selected.owners.service())
        runtime=successor.runtime(self.run)
        self.assertFalse(successor.process.history_audit_ready(self.run))
        result=runtime.on_market_event(self.case.event(1))
        self.assertIn('HISTORY_AUDIT_REQUIRED',result.reason_codes)
        state=successor.process.recover_current(self.run).state['runtime']
        self.assertIsNone(state['position'])
        self.assertFalse(state['forward']['last_healthy'])


if __name__=='__main__':unittest.main()
