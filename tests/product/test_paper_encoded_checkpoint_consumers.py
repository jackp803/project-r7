"""Actual LOCAL source owners; encoded profile selected in this test only.

Clock/source/native measurement boundary controlled by the existing source
fixture. Native diagnostic methods are unit-tested, not executable qualification.
"""
import json
import hashlib
import unittest
from unittest.mock import patch

from application.cloud.publication_history import PaperPublicationReadPort,PublicationHistoryError
from storage.paper_feedback import PaperFeedbackOutbox
from storage.paper_process import PaperProcessJournal
from storage.paper_state_codec import CODEC
from tests.product import test_paper_recorded_funding as funding_fixture
from tools.verify_paper_publication import NativePublicationFlow


def encoded_create(original):
    def create(journal,*args,**kwargs):
        kwargs['storage_profile']=CODEC
        return original(journal,*args,**kwargs)
    return create


class EncodedCheckpointConsumerTests(unittest.TestCase):
    def setUp(self):
        self.case=funding_fixture.PaperRecordedFundingTests();self.addCleanup(self.case.doCleanups)
        original=PaperProcessJournal.create_run
        with patch.object(PaperProcessJournal,'create_run',new=encoded_create(original)):self.case.close_pending()
        self.journal=self.case.service.process
        self.outbox=PaperFeedbackOutbox(self.journal)
        self.operation=self.outbox.queue(self.case.runtime)
        self.row=self.journal._db.execute('SELECT * FROM paper_feedback_publications WHERE operation_id=?',(self.operation,)).fetchone()
        self.document=json.loads(self.row['feedback_json'])
        self.reader=PaperPublicationReadPort(process_path=self.case.config.database_path,namespace='LOCAL_RESEARCH')

    def test_readonly_report_history_checks_original_logical_checkpoint_not_envelope_hash(self):
        try:history=self.reader.history(self.case.ref.run_id)
        except PublicationHistoryError:self.fail('Valid encoded E6 checkpoint hides actual owner report history')
        self.assertEqual(history['items'][0]['operation_id'],self.operation)
        self.assertEqual(history['items'][0]['feedback_hash'],self.row['feedback_hash'])
        self.assertEqual(self.outbox.publications()[0]['operation_id'],self.operation)

    def flow(self):
        flow=object.__new__(NativePublicationFlow)
        flow.data=self.case.config.local_data_root;flow.paper_run_id=self.case.ref.run_id
        flow.identity=self.document['source']
        return flow

    def test_native_diagnostic_run_facts_unit_reader_uses_same_logical_state(self):
        self.assertEqual(self.case.config.database_path.name,'canonical.sqlite3')
        try:facts=self.flow()._run_facts()
        except ValueError:self.fail('Native diagnostic reader compares physical envelope to logical state hash')
        state=self.journal.recover(self.case.ref.run_id)
        self.assertEqual(facts['state_hash'],'sha256:'+hashlib.sha256(state.state_json.encode()).hexdigest())
        self.assertEqual(facts['revision'],state.revision)

    def test_native_diagnostic_report_lineage_unit_reader_accepts_exact_logical_binding(self):
        try:self.flow()._paper_lineage(self.journal._db,self.row,self.document)
        except ValueError:self.fail('Native report lineage reader rejects exact encoded E6 checkpoint')

    def test_corrupt_physical_checkpoint_never_becomes_report_history_or_native_diagnostic_pass(self):
        db=self.journal._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_checkpoints_no_update'").fetchone()[0]
        db.execute('DROP TRIGGER paper_process_checkpoints_no_update')
        db.execute("UPDATE paper_process_checkpoints SET state_json='{}' WHERE run_id=? AND revision=?",
            (self.case.ref.run_id,self.row['run_revision']))
        db.execute(trigger)  # Restore exact schema; refusal must check actual bytes.
        with self.assertRaises(PublicationHistoryError):self.reader.history(self.case.ref.run_id)
        with self.assertRaises(ValueError):self.flow()._run_facts()
        with self.assertRaises(ValueError):self.flow()._paper_lineage(db,self.row,self.document)


class EncodedRecordedFundingRegressionTests(funding_fixture.PaperRecordedFundingTests):
    """Repeat all real source-owner lifecycle contracts on new physical rows."""
    def prepare(self,**kwargs):
        original=PaperProcessJournal.create_run
        with patch.object(PaperProcessJournal,'create_run',new=encoded_create(original)):
            return super().prepare(**kwargs)
