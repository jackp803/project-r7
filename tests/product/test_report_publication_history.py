"""Read actual owner-produced report history without constructing a writer."""
import importlib
import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import unittest
from unittest.mock import patch

import tests.product.test_research_queue as research_fixtures
import tests.product.test_paper_feedback_outbox as paper_fixtures


def delivery_fixture(case):
    from tests.application import test_cloud_bridge as fixtures
    helper=fixtures.CloudBridgeTests(methodName='runTest');helper.setUp();case.addCleanup(helper.doCleanups)
    return helper


def verify_delivery(case,reader,subject,flush,*,corrupt=False):
    from application.cloud.synced_folder import SyncedFolderCloudTransport
    from application.cloud.bridge_transport import RcloneCloudTransport
    bridge=delivery_fixture(case)
    original=reader.history(subject)['items'][0]
    staged=flush(SyncedFolderCloudTransport(bridge.stage,expected_root_id='bridge-fixture'))
    case.assertEqual(staged.local_staged,1)
    case.assertEqual(reader.history(subject)['items'][0]['state'],'LOCAL_STAGED')
    bridge.fake.outage=True
    case.assertEqual(flush(RcloneCloudTransport(bridge.bridge())).unavailable,1)
    case.assertEqual(reader.history(subject)['items'][0]['state'],'UNAVAILABLE')
    bridge.fake.outage=False;bridge.fake.corrupt_readback=corrupt
    result=flush(RcloneCloudTransport(bridge.bridge()))
    if corrupt:case.assertEqual(result.conflicts+result.unavailable,1)
    else:case.assertEqual(result.cloud_acknowledged,1)
    actual=reader.history(subject)['items'][0]
    case.assertIn(actual['state'],('CONFLICT','UNAVAILABLE') if corrupt else ('CLOUD_ACKNOWLEDGED',))
    for key in ('operation_id','artifact_hash','feedback_hash','queued_at'):case.assertEqual(actual[key],original[key])
    case.assertEqual(actual['attempts'],3)
    if not corrupt:
        for path in bridge.stage.rglob('*'):
            if path.is_file():case.assertEqual(path.read_bytes(),(bridge.remote/path.relative_to(bridge.stage)).read_bytes())
        case.assertEqual(flush(RcloneCloudTransport(bridge.bridge())).attempted,0)


def history_http(case,**ports):
    from tests.product import test_api_authority as fixtures
    from application.control_api.owner_services import OwnerControlServices
    from application.control_api.app import create_app
    from fastapi.testclient import TestClient
    helper=type('HistoryHTTPFixture',(fixtures.APIFixture,unittest.TestCase),{})(methodName='runTest')
    helper.setUp();case.addCleanup(helper.doCleanups)
    def forbidden():raise AssertionError('Report leaf opened E6 writer')
    owners=OwnerControlServices(helper.config,namespace='FIXTURE',clock=lambda:helper.clock[0],registry_factory=forbidden,**ports)
    client=TestClient(create_app(helper.config,auth=helper.auth,commands=helper.ledger,services=owners),
        base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000),raise_server_exceptions=False)
    case.addCleanup(client.close)
    return helper,client


class ResearchPublicationHistoryTests(unittest.TestCase):
    def setUp(self):
        self.case=research_fixtures.ResearchQueueTests(methodName='runTest');self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.enqueue();claim=self.case.queue.claim_next()
        self.job=self.case.queue.step(claim.run_id,claim.generation)
        self.assertEqual(self.job['state'],'COMPLETE')
        self.owner=self.case.service();self.addCleanup(self.owner.close)
        from application.cloud.feedback import queue_feedback
        self.operation=queue_feedback(self.owner,self.job['owner_run_id'])

    def reader(self,**kwargs):
        module=importlib.import_module('application.cloud.publication_history')
        return module.ResearchPublicationReadPort(queue_path=self.case.queue.path,
            research_path=self.case.root/'research.sqlite',namespace=kwargs.get('namespace','FIXTURE'))

    def test_actual_local_copy_ack_and_unavailable_history_remain_visible(self):
        from application.cloud.feedback import flush_feedback
        verify_delivery(self,self.reader(),self.job['run_id'],lambda transport:flush_feedback(self.owner.journal,transport,limit=1))

    def test_actual_wrong_byte_readback_history_is_not_an_ack(self):
        from application.cloud.feedback import flush_feedback
        verify_delivery(self,self.reader(),self.job['run_id'],lambda transport:flush_feedback(self.owner.journal,transport,limit=1),corrupt=True)

    def test_missing_schema_namespace_hardlink_and_hash_corruption_are_unavailable(self):
        module=importlib.import_module('application.cloud.publication_history');reader=self.reader()
        with self.assertRaises(module.PublicationHistoryError):self.reader(namespace='LOCAL_RESEARCH').history(self.job['run_id'])
        missing=self.case.root/'missing-history.sqlite';reader.research_path=missing
        with self.assertRaises(module.PublicationHistoryError):reader.history(self.job['run_id'])
        self.assertFalse(missing.exists())
        with closing(sqlite3.connect(missing)) as db:db.execute('CREATE TABLE unrelated(value TEXT)');db.commit()
        before=missing.read_bytes()
        with self.assertRaises(module.PublicationHistoryError):reader.history(self.job['run_id'])
        self.assertEqual(missing.read_bytes(),before)
        reader=self.reader();linked=self.case.root/'linked-history.sqlite';os.link(reader.research_path,linked)
        try:
            with self.assertRaises(module.PublicationHistoryError):reader.history(self.job['run_id'])
        finally:linked.unlink()
        with self.owner.journal._db:
            trigger=self.owner.journal._db.execute("SELECT sql FROM sqlite_master WHERE name='research_feedback_publications_immutable'").fetchone()[0]
            self.owner.journal._db.execute('DROP TRIGGER research_feedback_publications_immutable')
            self.owner.journal._db.execute("UPDATE research_feedback_publications SET artifact_hash=?",('sha256:'+'e'*64,))
            self.owner.journal._db.execute(trigger)
        with self.assertRaises(module.PublicationHistoryError):reader.history(self.job['run_id'])

    def test_owner_not_started_is_distinct_from_missing_report_store_and_strict_paging(self):
        reader=self.reader();module=importlib.import_module('application.cloud.publication_history')
        original=self.case.queue.resolve_request
        def distinct(submission,policy):
            selected=original('fixture-product',policy);selected['arguments']['submission_id']=submission;return selected
        self.case.queue.resolve_request=distinct
        pending=self.case.enqueue('new-job',submission_id='pending-history-owner')
        reader.research_path=self.case.root/'unused-store.sqlite'
        page=reader.history(pending['run_id']);self.assertEqual(page['status'],'NOT_RUN')
        self.assertEqual(page['reason_codes'],['REPORT_NOT_READY']);self.assertFalse(reader.research_path.exists())
        for values in ((True,0),(0,0),(101,0),(1,-1),(1,True)):
            with self.assertRaises(module.PublicationHistoryError):reader.history(pending['run_id'],limit=values[0],offset=values[1])

    def test_authenticated_leaf_does_not_use_queue_or_registry_writer(self):
        helper,client=history_http(self,research_publications=self.reader())
        url='/api/v1/research/runs/'+self.job['run_id']+'/publications'
        self.assertEqual(client.get(url).status_code,401)
        login=client.post('/api/v1/auth/login',json=dict(username='local-owner',password=helper.password,command_id='history-login',expected_revision=0),headers=helper.origin)
        self.assertEqual(login.status_code,200,login.text)
        with patch.object(self.case.queue,'_db',side_effect=AssertionError('GET opened queue writer')):
            response=client.get(url+'?limit=1&offset=0')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['data']['items'][0]['operation_id'],self.operation)
        self.assertEqual(client.get(url+'?limit=101').status_code,422)
        self.assertEqual(client.get(url+'?unknown=true').status_code,422)

    def test_malformed_payload_mapping_is_sanitized_with_exact_owned_schema(self):
        module=importlib.import_module('application.cloud.publication_history')
        db=self.owner.journal._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='research_feedback_publications_immutable'").fetchone()[0]
        with db:
            db.execute('DROP TRIGGER research_feedback_publications_immutable')
            db.execute("UPDATE research_feedback_publications SET payloads_json='[]'")
            db.execute(trigger)
        with self.assertRaises(module.PublicationHistoryError):self.reader().history(self.job['run_id'])
        helper,client=history_http(self,research_publications=self.reader())
        client.post('/api/v1/auth/login',json=dict(username='local-owner',password=helper.password,command_id='corrupt-history-login',expected_revision=0),headers=helper.origin)
        response=client.get('/api/v1/research/runs/'+self.job['run_id']+'/publications')
        self.assertEqual(response.status_code,503,response.text)
        self.assertNotIn('payloads_json',response.text)

    def test_different_actual_owner_family_and_seed_cannot_replace_the_job_report(self):
        from application.cloud.feedback import queue_feedback
        arguments=self.case.resolve('fixture-product','selected-fixture')['arguments']
        arguments.update(family_id='different-actual-family',seed=43)
        other=self.owner.run(**arguments)
        self.assertNotEqual(other.run_id,self.job['owner_run_id'])
        queue_feedback(self.owner,other.run_id)
        with self.case.queue._db() as db:
            db.execute('UPDATE research_queue_jobs SET owner_run_id=? WHERE run_id=?',(other.run_id,self.job['run_id']))
        module=importlib.import_module('application.cloud.publication_history')
        with self.assertRaises(module.PublicationHistoryError):self.reader().history(self.job['run_id'])
        from dataclasses import asdict
        with self.case.queue._db() as db:
            db.execute('UPDATE research_queue_jobs SET outcome_json=? WHERE run_id=?',(json.dumps(asdict(other)),self.job['run_id']))
        with self.assertRaises(module.PublicationHistoryError):self.reader().history(self.job['run_id'])

    def test_queue_owner_binding_is_rechecked_after_report_snapshot(self):
        module=importlib.import_module('application.cloud.publication_history');original=module.checked_feedback_record
        def concurrent_owner_change(*args):
            result=original(*args)
            with self.case.queue._db() as db:
                db.execute('UPDATE research_queue_jobs SET owner_run_id=NULL WHERE run_id=?',(self.job['run_id'],))
            return result
        with patch.object(module,'checked_feedback_record',side_effect=concurrent_owner_change):
            with self.assertRaises(module.PublicationHistoryError):self.reader().history(self.job['run_id'])

    def test_real_research_report_is_read_through_job_owner_binding_without_writer_or_regeneration(self):
        module=importlib.import_module('application.cloud.publication_history')
        from application.research.evidence import ResearchJournal
        from application.research.service import ResearchService
        reader=module.ResearchPublicationReadPort(queue_path=self.case.queue.path,
            research_path=self.case.root/'research.sqlite',namespace='FIXTURE')
        before=self.case.queue.get(self.job['run_id']);runs=self.owner.journal.runs()
        expected=self.owner.journal.pending_feedback_publications(1)[0][2]
        with (patch.object(self.case.queue,'_db',side_effect=AssertionError('RO history opened queue writer')),
              patch.object(ResearchJournal,'__init__',side_effect=AssertionError('RO history constructed journal writer')),
              patch.object(ResearchService,'__init__',side_effect=AssertionError('RO history constructed research owner')),
              patch('application.cloud.feedback.build_research_feedback',side_effect=AssertionError('RO history regenerated report'))):
            page=reader.history(self.job['run_id'],limit=1,offset=0)
        self.assertEqual(page['status'],'AVAILABLE');self.assertEqual(page['total'],1)
        row=page['items'][0]
        self.assertEqual(row['operation_id'],self.operation)
        self.assertEqual(row['run_id'],self.job['owner_run_id'])
        self.assertNotEqual(row['run_id'],self.job['run_id'])
        self.assertEqual(row['state'],'PENDING');self.assertEqual(row['artifact_hash'],expected)
        self.assertEqual(set(row),{'operation_id','run_id','state','feedback_hash','artifact_hash','attempts','queued_at'})
        self.assertEqual(self.case.queue.get(self.job['run_id']),before)
        self.assertEqual(self.owner.journal.runs(),runs)


class PaperPublicationHistoryTests(unittest.TestCase):
    def setUp(self):
        self.case=paper_fixtures.PaperFeedbackOutboxTests(methodName='runTest');self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.operation=self.case.queue();self.runtime=self.case.runtime
        self.path=Path(self.case.case.process._db.execute('PRAGMA database_list').fetchone()['file'])

    def reader(self):
        module=importlib.import_module('application.cloud.publication_history')
        return module.PaperPublicationReadPort(process_path=self.path,namespace='FIXTURE')

    def test_actual_local_copy_ack_and_unavailable_history_remain_visible(self):
        verify_delivery(self,self.reader(),self.runtime.run_id,lambda transport:self.case.outbox.flush(transport,limit=1))

    def test_actual_wrong_byte_readback_history_is_not_an_ack(self):
        verify_delivery(self,self.reader(),self.runtime.run_id,lambda transport:self.case.outbox.flush(transport,limit=1),corrupt=True)

    def test_historical_checkpoint_and_producer_are_not_relabelled_by_new_process(self):
        before=self.reader().history(self.runtime.run_id)
        self.runtime.on_market_event(self.case.case.event(4))
        second=self.case.queue();self.assertNotEqual(second,self.operation)
        self.case.case.process.begin_process(self.runtime.run_id,'history-successor',
            expected_generation=self.runtime.coordinator.generation,now=self.case.case.clock[0])
        first_page=self.reader().history(self.runtime.run_id,limit=1,offset=0)
        second_page=self.reader().history(self.runtime.run_id,limit=1,offset=1)
        self.assertEqual(first_page['total'],2);self.assertEqual(first_page['items'],before['items'])
        self.assertEqual(second_page['items'][0]['operation_id'],second)
        self.assertEqual(first_page['items'][0]['process_generation'],self.runtime.coordinator.generation)

    def test_authenticated_leaf_returns_only_original_report_metadata(self):
        helper,client=history_http(self,paper_publications=self.reader())
        url='/api/v1/paper/runs/'+self.runtime.run_id+'/publications'
        self.assertEqual(client.get(url).status_code,401)
        login=client.post('/api/v1/auth/login',json=dict(username='local-owner',password=helper.password,command_id='history-login',expected_revision=0),headers=helper.origin)
        self.assertEqual(login.status_code,200,login.text)
        response=client.get(url)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['data']['items'],self.reader().history(self.runtime.run_id)['items'])
        for secret in ('feedback_json','payloads_json','binding_json','instance_id',str(self.path)):
            self.assertNotIn(secret,response.text)

    def test_oversized_metadata_is_refused_before_report_materialization(self):
        module=importlib.import_module('application.cloud.publication_history')
        with self.case.case.process._db:
            self.case.case.process._db.execute('UPDATE paper_feedback_publications SET operation_id=?',('x'*65536,))
        original=module._bounded_row
        def forbid_report(db,table,*args,**kwargs):
            if table=='paper_feedback_publications':raise AssertionError('Corrupt metadata fetched before SQL preflight')
            return original(db,table,*args,**kwargs)
        with patch.object(module,'_bounded_row',side_effect=forbid_report):
            with self.assertRaises(module.PublicationHistoryError):self.reader().history(self.runtime.run_id,limit=100)

    def test_malformed_payload_mapping_is_typed_unavailable(self):
        module=importlib.import_module('application.cloud.publication_history')
        with self.case.case.process._db:
            self.case.case.process._db.execute("UPDATE paper_feedback_publications SET payloads_json='null'")
        with self.assertRaises(module.PublicationHistoryError):self.reader().history(self.runtime.run_id)

    def test_historical_producer_blob_is_sanitized_without_decoding_private_bytes(self):
        module=importlib.import_module('application.cloud.publication_history');db=self.case.case.process._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_generations_no_update'").fetchone()[0]
        with db:
            db.execute('DROP TRIGGER paper_process_generations_no_update')
            db.execute('UPDATE paper_process_generations SET instance_id=?',(sqlite3.Binary(b'SOURCE_ONLY_PRIVATE_PRODUCER'),))
            db.execute(trigger)
        with self.assertRaises(module.PublicationHistoryError):self.reader().history(self.runtime.run_id)

    def test_real_paper_report_keeps_original_checkpoint_without_owner_attachment_or_writer(self):
        module=importlib.import_module('application.cloud.publication_history')
        from storage.paper_process import PaperProcessJournal
        from storage.paper_feedback import PaperFeedbackOutbox
        reader=module.PaperPublicationReadPort(process_path=self.path,namespace='FIXTURE')
        before=self.case.case.process.recover(self.runtime.run_id)
        expected=self.case.outbox.publications()[0]
        with (patch.object(PaperProcessJournal,'__init__',side_effect=AssertionError('RO history constructed process writer')),
              patch.object(PaperProcessJournal,'begin_process',side_effect=AssertionError('RO history attached runtime')),
              patch.object(PaperFeedbackOutbox,'__init__',side_effect=AssertionError('RO history constructed outbox writer')),
              patch('application.cloud.paper_feedback.build_paper_feedback',side_effect=AssertionError('RO history regenerated report'))):
            page=reader.history(self.runtime.run_id,limit=1,offset=0)
        self.assertEqual(page['status'],'AVAILABLE');self.assertEqual(page['total'],1)
        row=page['items'][0]
        self.assertEqual(row['operation_id'],self.operation)
        for key in ('run_id','run_revision','process_generation','state','feedback_hash','artifact_hash','attempts'):
            self.assertEqual(row[key],expected[key])
        self.assertEqual(set(row),{'operation_id','run_id','run_revision','process_generation','state',
            'feedback_hash','artifact_hash','attempts','queued_at'})
        self.assertEqual(self.case.case.process.recover(self.runtime.run_id),before)


if __name__=='__main__':unittest.main()
