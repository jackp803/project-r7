"""Candidate index refusal/recovery; no manufactured financial decisions."""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application.cloud.manifest import canonical_bytes,byte_hash
from application.cloud.protocol import ArtifactBundle,CloudError,PublishReceipt
from application.cloud.synced_folder import SyncedFolderCloudTransport
from application.cloud import candidate_index as index
from application.research.evidence import ResearchEvidenceConflict,now_utc
from tests.application.test_candidate_index_integration_v02 import actual_candidate


def observations(service):
    return {row['observation_id']:dict(row) for row in service.ledger._db.execute(
        'SELECT * FROM research_holdout_observations ORDER BY observation_id')}


class CandidateIndexRecoveryV02Tests(unittest.TestCase):
    def test_raw_caller_index_and_real_noncandidate_cannot_enter_owner_outbox(self):
        from tests.application.test_product_assessment_binding import ProductAssessmentBindingTests
        from tests.application.test_research_robustness import selected
        with self.assertRaises(index.CandidateIndexError):index.build_candidate_index({'status':'PASS'},'invented')
        with TemporaryDirectory() as temporary:
            root=Path(temporary);selected(root)
            fixture=ProductAssessmentBindingTests()
            with fixture.service(root) as service:
                result=fixture.execute(service,risk=False)
                self.assertEqual('BACKTESTING',result.strategy_lifecycle)
                before=observations(service)
                with self.assertRaises(index.CandidateIndexError):index.queue_candidate_index(service,result.run_id)
                with self.assertRaises(ResearchEvidenceConflict):service.journal._enqueue_candidate_index({'status':'PASS'},now_utc())
                self.assertEqual((),service.journal.pending_candidate_index_publications(1))
                self.assertEqual(before,observations(service))

    def test_closed_public_index_rejects_parent_source_fields_and_arbitrary_html(self):
        with actual_candidate() as (_,service,result):
            original=index.build_candidate_index(service,result.run_id)
            bundle=index.candidate_index_bundle(original)
            for label,mutate in (
                ('extra',lambda v:v.update(provider_account_id='SYNTHETIC_FORBIDDEN_FIELD')),
                ('namespace',lambda v:v.update(namespace='LIVE')),
                ('authority',lambda v:v.update(financial_authority='PAPER')),
                ('parent',lambda v:v['evidence'][2].update(parent_evidence_id=v['evidence'][0]['evidence_id'])),
                ('source',lambda v:v['source'].update(execution='HOSTED')),
                ('reference',lambda v:v['evidence'][3].update(result_ref='research:other/product_assessment')),
                ('hash',lambda v:v['dataset'].update(manifest_hash='not-a-hash'))):
                value=deepcopy(original);mutate(value)
                with self.subTest(label=label),self.assertRaises((ValueError,CloudError)):
                    index.candidate_index_bundle(value)
            for payloads in ({**bundle.payloads,'report.html':b'<b>synthetic wrong renderer</b>'},
                             {**bundle.payloads,'candidate_manifest.json':b'{}'},
                             {'evidence_index.json':bundle.payloads['evidence_index.json']},
                             {**bundle.payloads,'report.html':b'x'*(256*1024+1)}):
                with self.subTest(keys=set(payloads)),self.assertRaises((ValueError,CloudError)):
                    index.validate_candidate_index_publication(bundle.logical_path,payloads)
            self.assertEqual(original,index.validate_candidate_index_publication(bundle.logical_path,dict(bundle.payloads)))

    def test_unavailable_after_actual_local_stage_recovers_with_same_bytes_and_no_extra_exposure(self):
        with actual_candidate() as (root,service,result),TemporaryDirectory() as temporary:
            stage=Path(temporary);(stage/'.r7-root.json').write_bytes(canonical_bytes(dict(root_id='candidate-recovery')))
            transport=SyncedFolderCloudTransport(stage,expected_root_id='candidate-recovery')
            operation=index.queue_candidate_index(service,result.run_id)
            before=observations(service)
            class Interrupted:
                def publish(self,bundle,op):
                    transport.publish(bundle,op)
                    raise CloudError('UNAVAILABLE','SYNTHETIC_LOST_LOCAL_ACK')
            first=index.flush_candidate_indexes(service.journal,Interrupted(),limit=1)
            self.assertEqual((1,1),(first.attempted,first.unavailable))
            row=service.journal._db.execute('SELECT * FROM research_candidate_index_publications').fetchone()
            self.assertEqual(('UNAVAILABLE',1),(row['state'],row['attempts']))
            original={p.relative_to(stage).as_posix():p.read_bytes() for p in stage.rglob('*') if p.is_file()}
            from tests.application.test_product_assessment_binding import ProductAssessmentBindingTests
            with ProductAssessmentBindingTests().service(root) as restarted:
                self.assertEqual(operation,index.queue_candidate_index(restarted,result.run_id))
                self.assertEqual(before,observations(restarted))
                second=index.flush_candidate_indexes(restarted.journal,transport,limit=1)
                self.assertEqual((1,1,0),(second.attempted,second.local_staged,second.cloud_acknowledged))
                self.assertEqual((),restarted.journal.pending_candidate_index_publications(1,include_local_staged=False))
                self.assertEqual(original,{p.relative_to(stage).as_posix():p.read_bytes() for p in stage.rglob('*') if p.is_file()})
                self.assertEqual(before,observations(restarted))

    def test_wrong_transport_receipt_never_acks_and_acknowledged_row_cannot_regress(self):
        with actual_candidate() as (_,service,result):
            operation=index.queue_candidate_index(service,result.run_id)
            _,_,artifact=service.journal.pending_candidate_index_publications(1)[0]
            class WrongReceipt:
                def publish(self,bundle,op):
                    return PublishReceipt(op,'CLOUD_ACKNOWLEDGED','sha256:'+'0'*64)
            summary=index.flush_candidate_indexes(service.journal,WrongReceipt(),limit=1)
            self.assertEqual((1,0),(summary.unavailable,summary.cloud_acknowledged))
            row=service.journal._db.execute('SELECT * FROM research_candidate_index_publications').fetchone()
            self.assertEqual('UNAVAILABLE',row['state'])
            with self.assertRaises(ResearchEvidenceConflict):
                service.journal.record_candidate_index_publication(operation,'CLOUD_ACKNOWLEDGED',artifact_hash='sha256:'+'0'*64)
            # Controlled transport contract response only, not real cloud proof.
            service.journal.record_candidate_index_publication(operation,'CLOUD_ACKNOWLEDGED',artifact_hash=artifact)
            before=dict(service.journal._db.execute('SELECT * FROM research_candidate_index_publications').fetchone())
            with self.assertRaises(ResearchEvidenceConflict):
                service.journal.record_candidate_index_publication(operation,'UNAVAILABLE')
            self.assertEqual(before,dict(service.journal._db.execute('SELECT * FROM research_candidate_index_publications').fetchone()))
            self.assertEqual((),service.journal.pending_candidate_index_publications(1))

    def test_concurrent_real_journal_ack_cannot_be_overwritten_by_stale_unavailable_writer(self):
        import threading
        from application.research import evidence
        from application.research.evidence import ResearchJournal
        with actual_candidate() as (root,service,result):
            operation=index.queue_candidate_index(service,result.run_id)
            _,_,artifact=service.journal.pending_candidate_index_publications(1)[0]
            ready=threading.Event();start=threading.Event();attempt_done=threading.Event();writer_done=threading.Event()
            failures=[];outcomes=[]
            def acknowledger():
                try:
                    with ResearchJournal(root/'research.sqlite') as second:
                        # Test-only finite lock probe; production keeps5000ms.
                        second._db.execute('PRAGMA busy_timeout=50');ready.set()
                        if not start.wait(3):raise AssertionError('Writer did not reach actual row-read seam')
                        try:
                            second.record_candidate_index_publication(operation,'CLOUD_ACKNOWLEDGED',artifact_hash=artifact)
                            outcomes.append('ACK_COMMITTED_WHILE_FIRST_WRITER_PAUSED')
                        except sqlite3.OperationalError as error:
                            if 'locked' not in str(error):raise
                            outcomes.append('SECOND_WRITER_SERIALIZED')
                            attempt_done.set()
                            if not writer_done.wait(3):raise AssertionError('First writer did not finish')
                            second.record_candidate_index_publication(operation,'CLOUD_ACKNOWLEDGED',artifact_hash=artifact)
                        finally:attempt_done.set()
                except BaseException as error:
                    failures.append(type(error).__name__);ready.set();attempt_done.set()
            thread=threading.Thread(target=acknowledger)
            checked=evidence._checked_candidate_index;reached=[]
            def interleave(journal,row):
                bundle=checked(journal,row)
                if journal is service.journal and not reached:
                    reached.append(True);start.set()
                    if not attempt_done.wait(3):raise AssertionError('Second writer probe did not complete')
                return bundle
            thread.start()
            try:
                self.assertTrue(ready.wait(3))
                with patch.object(evidence,'_checked_candidate_index',side_effect=interleave):
                    service.journal.record_candidate_index_publication(operation,'UNAVAILABLE')
            finally:
                writer_done.set();start.set();thread.join(timeout=6)
            self.assertFalse(thread.is_alive());self.assertEqual([],failures);self.assertTrue(reached)
            row=service.journal._db.execute('SELECT * FROM research_candidate_index_publications').fetchone()
            self.assertEqual(1,len(outcomes))
            self.assertEqual('CLOUD_ACKNOWLEDGED',row['state'],outcomes)
            self.assertEqual((),service.journal.pending_candidate_index_publications(1))

    def test_disclosure_is_durable_before_enqueue_failure_and_retry_is_idempotent(self):
        with actual_candidate() as (_,service,result):
            before=observations(service)
            with patch.object(service.journal,'_enqueue_candidate_index',side_effect=OSError('synthetic local outbox interruption')):
                with self.assertRaises(OSError):index.queue_candidate_index(service,result.run_id)
            exposed=observations(service)
            self.assertEqual(1,len(set(exposed)-set(before)))
            self.assertEqual((),service.journal.pending_candidate_index_publications(1))
            operation=index.queue_candidate_index(service,result.run_id)
            self.assertEqual(exposed,observations(service))
            self.assertEqual(operation,index.queue_candidate_index(service,result.run_id))
            self.assertEqual(exposed,observations(service))

    def test_actual_outbox_content_delete_and_replace_guards_preserve_original_row(self):
        with actual_candidate() as (_,service,result):
            index.queue_candidate_index(service,result.run_id)
            db=service.journal._db
            before=dict(db.execute('SELECT * FROM research_candidate_index_publications').fetchone())
            db.execute('PRAGMA recursive_triggers=OFF')
            for statement in (
                "UPDATE research_candidate_index_publications SET index_json='{}'",
                "UPDATE research_candidate_index_publications SET logical_path='candidates/changed'",
                "UPDATE research_candidate_index_publications SET created_at='changed'",
                'DELETE FROM research_candidate_index_publications',
                'INSERT OR REPLACE INTO research_candidate_index_publications SELECT * FROM research_candidate_index_publications',
                "INSERT OR REPLACE INTO research_candidate_index_publications SELECT 'other-operation',run_id,index_json,index_hash,logical_path,payloads_json,artifact_hash,state,attempts,created_at FROM research_candidate_index_publications"):
                with self.subTest(statement=statement),self.assertRaises(sqlite3.IntegrityError):
                    with db:db.execute(statement)
                self.assertEqual(before,dict(db.execute('SELECT * FROM research_candidate_index_publications').fetchone()))
            for limit in (True,0,101):
                with self.subTest(limit=limit),self.assertRaises(ValueError):service.journal.pending_candidate_index_publications(limit)

    def test_substituted_report_subject_is_refused_before_disclosure_or_outbox(self):
        with actual_candidate() as (_,service,result):
            original=service.report;before=observations(service)
            def changed(run_id):
                value=original(run_id);value['inputs']['dataset_manifest_hash']='sha256:'+'0'*64
                return value
            with patch.object(service,'report',side_effect=changed):
                with self.assertRaises(index.CandidateIndexError):index.queue_candidate_index(service,result.run_id)
            self.assertEqual(before,observations(service))
            self.assertEqual((),service.journal.pending_candidate_index_publications(1))

    def test_exact_legacy_research_journal_ddl_remains_accepted_without_new_owner_mutation(self):
        from tests.application.upgrade_preflight_fixture import make_verified_bundle,source_database_hashes,bundle_hashes
        from tests.application.upgrade_preflight_complete_fixture import _seal
        from application.platform.upgrade_preflight import preflight_product_upgrade
        c=make_verified_bundle(self)
        migrations=Path(__file__).resolve().parents[2]/'src/application/migrations'
        with closing(sqlite3.connect(c.config.local_data_root/'research.sqlite')) as db:
            for name in ('0002_research_attempts.sql','0007_research_feedback_outbox.sql'):
                db.executescript((migrations/name).read_text(encoding='utf-8'))
        c=_seal(self,c,'legacy-research-journal')
        observed=preflight_product_upgrade(c.config,c.backup,config_path=c.config_path)
        self.assertEqual('COMPATIBLE',observed['roles']['research']['status'])
        self.assertEqual(c.source_hashes,source_database_hashes(c.config))
        self.assertEqual(c.backup_hashes,bundle_hashes(c.backup))


if __name__=='__main__':unittest.main()
