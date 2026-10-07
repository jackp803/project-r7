import copy,importlib,json,unittest
from pathlib import Path
from tests.product import test_paper_runtime_v02 as fixtures
from application.cloud.protocol import CloudError,PublishReceipt

class PaperFeedbackOutboxTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('storage.paper_feedback')
        self.case=fixtures.PaperRuntimeV02Tests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        from storage._sqlite_registry import _apply_migrations
        _apply_migrations(self.case.process._db)
        self.runtime=self.case.start();self.outbox=self.module.PaperFeedbackOutbox(self.case.process)
        self.runtime.on_market_event(self.case.event(0,bars=True))
        self.runtime.on_market_event(self.case.event(1))
        self.runtime.on_market_event(self.case.event(2,'60020'))
        self.runtime.on_market_event(self.case.event(3,'60020'))
    def queue(self,**options):return self.outbox.queue(self.runtime,**options)
    def test_current_owner_report_and_outbox_reference_are_durable_and_idempotent(self):
        before=self.case.process.recover(self.runtime.run_id)
        first=self.queue();self.assertEqual(self.queue(),first)
        row=self.outbox.publications()[0]
        self.assertEqual(row['state'],'PENDING');self.assertEqual(row['run_revision'],before.revision)
        self.assertEqual(row['process_generation'],before.process_generation)
        self.assertEqual(len(self.outbox.pending(10)),1)
        after=self.case.process.recover(self.runtime.run_id)
        self.assertEqual((before.process_generation,before.revision,before.state_json),(after.process_generation,after.revision,after.state_json))
        reopened=self.module.PaperFeedbackOutbox(self.case.process)
        self.assertEqual(reopened.pending(10),self.outbox.pending(10))
    def test_checkpoint_change_after_computation_rolls_back_all_outbox_writes(self):
        def fault(stage):
            self.assertEqual(stage,'AFTER_REPORT_BEFORE_OUTBOX')
            self.runtime.on_market_event(self.case.event(4))
        with self.assertRaises(ValueError):self.queue(fault_hook=fault)
        self.assertEqual(self.outbox.publications(),[])
    def test_replacement_process_cannot_commit_a_computed_old_owner_report(self):
        def fault(stage):
            self.case.process.begin_process(self.runtime.run_id,'replacement-publisher-race',expected_generation=self.runtime.coordinator.generation,now=self.case.clock[0])
        with self.assertRaises(ValueError):self.queue(fault_hook=fault)
        self.assertEqual(self.outbox.publications(),[])
    def test_changing_runtime_object_generation_cannot_relabel_precomputed_report(self):
        def fault(stage):
            self.runtime.coordinator.generation=self.case.process.begin_process(self.runtime.run_id,'replacement-object-race',
                expected_generation=self.runtime.coordinator.generation,now=self.case.clock[0])
        with self.assertRaises(ValueError):self.queue(fault_hook=fault)
        self.assertEqual(self.outbox.publications(),[])
    def test_network_call_cannot_run_inside_an_existing_sqlite_transaction(self):
        self.queue();self.case.process._db.execute('BEGIN IMMEDIATE')
        class Forbidden:
            def publish(self,*args):raise AssertionError('Network call ran inside writer transaction')
        try:
            with self.assertRaises(ValueError):self.outbox.flush(Forbidden(),limit=1)
        finally:self.case.process._db.rollback()
    def test_bounded_pending_capacity_preserves_canonical_runtime_and_prior_publication(self):
        from unittest.mock import patch
        first=self.queue();self.runtime.on_market_event(self.case.event(4))
        before=self.case.process.recover(self.runtime.run_id)
        with patch.object(self.module,'MAX_PENDING',1),self.assertRaises(ValueError):self.queue()
        self.assertEqual([row['operation_id'] for row in self.outbox.publications()],[first])
        after=self.case.process.recover(self.runtime.run_id)
        self.assertEqual((after.revision,after.state_json),(before.revision,before.state_json))
    def test_actual_consistent_sqlite_backup_preserves_report_and_outbox_lineage(self):
        import sqlite3
        from storage.paper_process import open_paper_process_journal
        self.queue();destination=self.case.root/'consistent-feedback-copy.sqlite'
        with sqlite3.connect(destination) as snapshot:self.case.process._db.backup(snapshot)
        with open_paper_process_journal(destination) as recovered:
            copy=self.module.PaperFeedbackOutbox(recovered)
            self.assertEqual(copy.pending(10),self.outbox.pending(10))
    def test_network_ack_failure_retains_one_item_and_later_ack_does_not_republish(self):
        operation=self.queue();calls=[]
        class Transport:
            available=False
            def publish(inner,bundle,identifier):
                calls.append(identifier)
                if not inner.available:raise CloudError('UNAVAILABLE','CONTROLLED_OFFLINE_OUTAGE')
                artifact=self.outbox.pending(1)[0][2]
                return PublishReceipt(identifier,'CLOUD_ACKNOWLEDGED',artifact)
        transport=Transport()
        first=self.outbox.flush(transport,limit=10);self.assertEqual(first.unavailable,1)
        self.assertEqual(self.outbox.publications()[0]['state'],'UNAVAILABLE')
        transport.available=True;second=self.outbox.flush(transport,limit=10)
        self.assertEqual(second.cloud_acknowledged,1);self.assertEqual(self.outbox.publications()[0]['state'],'CLOUD_ACKNOWLEDGED')
        self.assertEqual(self.outbox.flush(transport,limit=10).attempted,0);self.assertEqual(calls,[operation,operation])
    def test_local_stage_is_not_remote_acknowledgement_and_wrong_hash_is_not_accepted(self):
        operation=self.queue()
        class Transport:
            valid=True
            def publish(inner,bundle,identifier):
                artifact=self.outbox.pending(1)[0][2] if inner.valid else 'sha256:'+'e'*64
                return PublishReceipt(identifier,'LOCAL_STAGED',artifact)
        transport=Transport();result=self.outbox.flush(transport,limit=1)
        self.assertEqual(result.local_staged,1);self.assertEqual(result.cloud_acknowledged,0)
        self.assertEqual(self.outbox.publications()[0]['state'],'LOCAL_STAGED')
        transport.valid=False;self.assertEqual(self.outbox.flush(transport,limit=1).unavailable,1)
        self.assertEqual(self.outbox.publications()[0]['state'],'UNAVAILABLE')
    def test_crash_after_upload_before_ack_retries_same_immutable_operation(self):
        operation=self.queue();calls=[]
        class Transport:
            def publish(inner,bundle,identifier):
                calls.append(identifier)
                return PublishReceipt(identifier,'CLOUD_ACKNOWLEDGED',self.outbox.pending(1)[0][2])
        def crash(stage):raise RuntimeError('CONTROLLED_PUBLISHER_CRASH')
        with self.assertRaises(RuntimeError):self.outbox.flush(Transport(),limit=1,fault_hook=crash)
        self.assertEqual(self.outbox.publications()[0]['state'],'PENDING')
        self.assertEqual(self.outbox.flush(Transport(),limit=1).cloud_acknowledged,1)
        self.assertEqual(calls,[operation,operation])
    def test_tampered_stored_report_is_rejected_before_any_transport_call(self):
        self.queue();self.case.process._db.execute("UPDATE paper_feedback_publications SET feedback_json='{}'")
        class Forbidden:
            def publish(self,*args):raise AssertionError('Tampered report reached transport')
        with self.assertRaises(ValueError):self.outbox.flush(Forbidden(),limit=1)
    def test_stored_producer_generation_cannot_be_relabelled_as_an_existing_newer_generation(self):
        self.queue()
        replacement=self.case.process.begin_process(self.runtime.run_id,'existing-but-not-report-producer',
            expected_generation=self.runtime.coordinator.generation,now=self.case.clock[0])
        self.case.process._db.execute('UPDATE paper_feedback_publications SET process_generation=?',(replacement,))
        with self.assertRaises(ValueError):self.outbox.pending(10)
    def test_historical_publication_keeps_original_producer_after_legitimate_runtime_replacement(self):
        self.queue();before=self.outbox.pending(10);original=self.outbox.publications()[0]['process_generation']
        self.case.process.begin_process(self.runtime.run_id,'new-runtime-history-test',expected_generation=original,now=self.case.clock[0])
        self.assertEqual(self.outbox.pending(10),before)
        self.assertEqual(self.outbox.publications()[0]['process_generation'],original)
    def test_stored_producer_instance_is_immutable_in_actual_owner_journal(self):
        import sqlite3
        self.queue();original=self.outbox.pending(10)
        with self.assertRaises(sqlite3.IntegrityError):
            self.case.process._db.execute('UPDATE paper_process_generations SET instance_id=? WHERE run_id=? AND generation=?',
                ('substituted-instance',self.runtime.run_id,self.runtime.coordinator.generation))
        self.assertEqual(self.outbox.pending(10),original)
    def test_invalid_batch_limits_and_replaced_journal_are_rejected(self):
        for limit in (0,101,True):
            with self.subTest(limit=limit),self.assertRaises(ValueError):self.outbox.pending(limit)
        with self.assertRaises(ValueError):self.module.PaperFeedbackOutbox(object())

if __name__=='__main__':unittest.main()
