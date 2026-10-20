"""Actual diagnostic owners and authenticated observations; no financial grant."""
from contextlib import closing,contextmanager
from datetime import datetime,timedelta,timezone
import sqlite3
import unittest
from unittest.mock import patch

from application.control_api.services import LocalControlServices
from application.control_api.paper_ports import PaperStartControlPort
from application.research.queue import ResearchQueueError
from registry import StrategyIdentity
from tests.product import test_api_authority as auth_fixtures
from tests.product import test_api_owner_services as owner_fixtures
from tests.product import test_research_queue as queue_fixtures
from tests.product import two_version_fixtures
from tests.application import test_runtime_process_supervision as process_fixtures


def fixture(test,kind):
    actual=kind(methodName='runTest');actual.setUp();test.addCleanup(actual.doCleanups)
    return actual


class UI01ObservationTests(unittest.TestCase):
    def test_unconfigured_authenticated_views_keep_unknowns_and_config_commitment_stable(self):
        class Actual(auth_fixtures.APIFixture,unittest.TestCase):pass
        f=fixture(self,Actual);f.login()
        def read(route):
            result=f.client.get('/api/v1/'+route);self.assertEqual(200,result.status_code,result.text)
            return result.json()
        first=read('settings');before=first['metadata']['config_hash']
        self.assertEqual('AVAILABLE',first['data']['resource_limits']['status'])
        self.assertEqual({'research_worker_count':f.config.research_worker_count},first['data']['resource_limits']['facts'])
        for key,status in (('clock_health','UNAVAILABLE'),('credential_presence','UNAVAILABLE'),('backup','NOT_CONFIGURED'),('transport_test','NOT_RUN')):
            value=first['data'][key]
            self.assertEqual(status,value['status']);self.assertIsNone(value['as_of'])
            self.assertEqual({},value['facts']);self.assertEqual('NONE',value['financial_authority'])
        overview=read('overview')['data']
        for key in ('strategy_subjects','research_stage_counts','alerts'):
            self.assertEqual('NOT_CONFIGURED',overview[key]['status']);self.assertEqual({},overview[key]['facts'])
        health=read('health')['data']
        for key in ('risk','execution','preflight','external_consumer'):
            self.assertEqual('UNAVAILABLE',health[key]['status']);self.assertIsNone(health[key]['as_of'])
        for role,value in health['components'].items():
            self.assertEqual('AVAILABLE',value['status']);self.assertEqual(role,value['facts']['role'])
            self.assertEqual('NOT_STARTED',value['facts']['status']);self.assertIsNone(value['as_of'])
        self.assertFalse((f.root/'process-supervision.sqlite').exists())
        f.clock[0]+=timedelta(seconds=1)
        second=read('settings')
        self.assertNotEqual(first['data']['resource_limits']['checked_at'],second['data']['resource_limits']['checked_at'])
        for route in ('settings','health','overview'):self.assertEqual(before,read(route)['metadata']['config_hash'])
        body=dict(command_id='ui01-real-settings',expected_revision=first['data']['revision'],display_timezone='UTC',scan_interval=47)
        headers=dict(f.origin,**{'X-R7-CSRF':f.csrf})
        changed=f.client.put('/api/v1/settings/non-secret',json=body,headers=headers)
        self.assertEqual(200,changed.status_code,changed.text)
        self.assertNotEqual(before,read('settings')['metadata']['config_hash'])
        self.assertEqual(changed.json(),f.client.put('/api/v1/settings/non-secret',json=body,headers=headers).json())

    def test_explicit_selected_version_matches_actual_registry_and_never_selects_newest(self):
        f=fixture(self,owner_fixtures.APIOwnerServicesTests)
        values=two_version_fixtures.prepare_two_version_context(f)
        listing=f.client.get('/api/v1/strategies').json()['data']
        jobs=f.client.get('/api/v1/research/runs').json()['data']
        self.assertEqual('NOT_CONFIGURED',f.client.get('/api/v1/overview').json()['data']['strategy_subjects']['status'])
        selected=values['first'];identity=StrategyIdentity(selected['strategy_id'],selected['strategy_version'])
        def forbidden():raise AssertionError('Diagnostic must not start or construct Paper owner')
        f.owners.paper_start=PaperStartControlPort(namespace='FIXTURE',service_factory=forbidden,strategy_identity=identity)
        for _ in range(2):
            response=f.client.get('/api/v1/overview');self.assertEqual(200,response.status_code,response.text)
            value=response.json()['data']['strategy_subjects']
            self.assertEqual('AVAILABLE',value['status']);self.assertIsNone(value['as_of'])
            self.assertEqual('NONE',value['financial_authority'])
            self.assertEqual([dict(strategy_id=identity.strategy_id,strategy_version=identity.strategy_version,
                content_hash=selected['content_hash'],relationship='CONFIGURED_SELECTION')],value['facts']['items'])
        self.assertEqual(listing,f.client.get('/api/v1/strategies').json()['data'])
        self.assertEqual(jobs,f.client.get('/api/v1/research/runs').json()['data'])
        self.assertFalse((f.root/'process-supervision.sqlite').exists())

    def test_genuine_failed_owner_projects_historical_alert_identity_and_time(self):
        f=fixture(self,owner_fixtures.APIOwnerServicesTests);f.enqueue()
        original=f.queue.service_factory
        @contextmanager
        def failing():
            with original() as owner,patch.object(owner,'run',side_effect=RuntimeError('SOURCE_ONLY_UI01_FAILURE')):yield owner
        f.queue.service_factory=failing
        claim=f.queue.claim_next();failed=f.queue.step(claim.run_id,claim.generation)
        self.assertEqual('FAILED',failed['state'])
        f.clock[0]+=timedelta(seconds=1)
        alert=f.client.get('/api/v1/alerts').json()['data']['items'][0]
        response=f.client.get('/api/v1/overview');self.assertEqual(200,response.status_code,response.text)
        value=response.json()['data']['alerts']
        self.assertEqual([alert],value['facts']['items']);self.assertEqual(1,value['facts']['total'])
        self.assertEqual(failed['observed_at'],value['as_of']);self.assertNotEqual(value['as_of'],value['checked_at'])
        self.assertNotIn('SOURCE_ONLY_UI01_FAILURE',response.text)

    def test_real_runtime_heartbeat_has_original_source_times_and_no_config_churn(self):
        f=fixture(self,process_fixtures.RuntimeProcessSupervisionTests)
        services=LocalControlServices(f.config,namespace='LOCAL_RESEARCH',clock=lambda:datetime.now(timezone.utc))
        config_hash=services.metadata('ui01')['config_hash']
        with f.session('runtime') as owner:
            observed=services.view('health')
            self.assertEqual('PROCESS_RECENT_HEARTBEAT',observed['runtime'])
            first=observed['components']['runtime']
            facts=first['facts']
            self.assertEqual('RECENT_HEARTBEAT',facts['status']);self.assertEqual('AVAILABLE',first['status'])
            self.assertEqual(owner.identity['process_generation_id'],facts['process_generation_id'])
            self.assertEqual(owner.identity['started_at'],facts['started_at'])
            self.assertEqual(owner.identity['config_hash'],facts['config_hash'])
            self.assertEqual(facts['heartbeat_at'],first['as_of'])
            self.assertGreaterEqual(first['checked_at'],first['as_of'])
            f.wait_heartbeat(owner,facts['heartbeat_sequence'])
            health=services.view('health');second=health['components']['runtime']
            self.assertGreater(second['facts']['heartbeat_sequence'],facts['heartbeat_sequence'])
            self.assertEqual(facts['started_at'],second['facts']['started_at'])
            self.assertEqual(config_hash,services.metadata('ui01')['config_hash'])
            for key in ('risk','execution','preflight','external_consumer'):
                self.assertEqual('UNAVAILABLE',health[key]['status']);self.assertEqual({},health[key]['facts'])
        stopped=services.view('health')['components']['runtime']
        self.assertEqual('STOPPED',stopped['facts']['status'])

    def test_corrupt_one_supervision_component_preserves_other_observations_and_source_bytes(self):
        f=fixture(self,process_fixtures.RuntimeProcessSupervisionTests)
        services=LocalControlServices(f.config,namespace='LOCAL_RESEARCH',clock=lambda:datetime.now(timezone.utc))
        with f.session('control'),f.session('research'):pass
        path=f.config.local_data_root/'process-supervision.sqlite'
        with closing(sqlite3.connect(path)) as db,db:
            db.execute("UPDATE process_sessions SET generation='CORRUPT_METADATA' WHERE role='research'")
        before=path.read_bytes()
        value=services.view('health')
        from application.control_api.dto import HealthView
        HealthView.model_validate(value)
        self.assertEqual('UNAVAILABLE',value['components']['research']['status'])
        self.assertEqual('SUPERVISION_STORAGE_FAILURE',value['components']['research']['facts']['status'])
        self.assertIsNone(value['components']['research']['as_of'])
        self.assertEqual('STOPPED',value['components']['control']['facts']['status'])
        self.assertEqual('AVAILABLE',value['components']['control']['status'])
        self.assertEqual(before,path.read_bytes())

    def test_naive_and_non_utc_source_times_are_unavailable_per_component(self):
        f=fixture(self,process_fixtures.RuntimeProcessSupervisionTests)
        services=LocalControlServices(f.config,namespace='LOCAL_RESEARCH',clock=lambda:datetime.now(timezone.utc))
        with f.session('research'):pass
        path=f.config.local_data_root/'process-supervision.sqlite'
        for malformed in ('2026-10-21T00:00:00.000000','2026-10-21T00:00:00.000000+08:00'):
            with self.subTest(source_time=malformed):
                with closing(sqlite3.connect(path)) as db,db:
                    db.execute("UPDATE process_sessions SET started_at=? WHERE role='research'",(malformed,))
                before=path.read_bytes();value=services.view('health')['components']['research']
                self.assertEqual('UNAVAILABLE',value['status']);self.assertIsNone(value['as_of'])
                self.assertIsNone(value['facts']['started_at']);self.assertEqual(before,path.read_bytes())


class ResearchStageObservationTests(unittest.TestCase):
    def setUp(self):self.f=fixture(self,queue_fixtures.ResearchQueueTests)

    def test_empty_read_is_distinct_from_missing_and_never_initializes_a_store(self):
        q=self.f.queue;before=q.path.read_bytes()
        with patch.object(q,'_db',side_effect=AssertionError('No writable view factory')),patch.object(q,'service_factory',side_effect=AssertionError('No research owner work')):
            self.assertEqual(dict(items=[],total_jobs=0,as_of=None),q.state_stage_counts())
        self.assertEqual(before,q.path.read_bytes())
        original=q.path;q.path=self.f.root/'missing-stage-count.sqlite'
        try:
            with self.assertRaises(ResearchQueueError) as error:q.state_stage_counts()
            self.assertEqual('RESEARCH_QUEUE_COUNTS_UNAVAILABLE',error.exception.code)
            self.assertFalse(q.path.exists())
        finally:q.path=original

    def test_actual_queued_cancelled_and_completed_stages_read_live_wal_without_owner_work(self):
        f=self.f;q=f.queue;base=q.resolve_request
        def distinct(submission,policy):
            selected=base('fixture-product',policy);selected['arguments']['submission_id']=submission;return selected
        q.resolve_request=distinct
        with q._db() as keeper:
            keeper.execute('SELECT COUNT(*) FROM research_queue_jobs').fetchone()
            a=f.enqueue('first-stage-job',submission_id='fixture-stage-first')
            f.clock[0]+=timedelta(seconds=1)
            b=f.enqueue('second-stage-job',submission_id='fixture-stage-second')
            q.cancel(a['run_id'],a['revision'],'cancel-first-stage',actor='local-owner')
            claim=q.claim_next();self.assertEqual(b['run_id'],claim.run_id)
            q.step(claim.run_id,claim.generation)
            actual=[q.get(row['run_id']) for row in (a,b)]
            self.assertEqual({'CANCELED','COMPLETE'},{row['state'] for row in actual})
            before=q.path.read_bytes()
            with patch.object(q,'_db',side_effect=AssertionError('No writable view factory')),patch.object(q,'service_factory',side_effect=AssertionError('No research owner work')):
                observed=q.state_stage_counts()
            expected=[dict(state=row['state'],stage=row['stage'],count=1,last_observed_at=row['observed_at']) for row in actual]
            self.assertEqual(sorted(expected,key=lambda row:(row['state'],row['stage'] or '')),observed['items'])
            self.assertEqual(2,observed['total_jobs']);self.assertEqual(max(row['observed_at'] for row in actual),observed['as_of'])
            self.assertEqual(before,q.path.read_bytes())

    def test_malformed_older_timestamp_cannot_hide_behind_a_valid_maximum(self):
        f=self.f;q=f.queue
        base=q.resolve_request
        def distinct(submission,policy):
            selected=base('fixture-product',policy);selected['arguments']['submission_id']=submission;return selected
        q.resolve_request=distinct
        first=f.enqueue('first-timestamp',submission_id='fixture-time-first')
        f.clock[0]+=timedelta(seconds=1)
        f.enqueue('second-timestamp',submission_id='fixture-time-second')
        with q._db() as db:db.execute("UPDATE research_queue_jobs SET updated_at='2020-01-01T00:00:00Z' WHERE run_id=?",(first['run_id'],))
        before=q.path.read_bytes()
        with self.assertRaises(ResearchQueueError) as error:q.state_stage_counts()
        self.assertEqual('RESEARCH_QUEUE_COUNTS_UNAVAILABLE',error.exception.code)
        self.assertEqual(before,q.path.read_bytes())

    def test_unknown_schema_and_namespace_are_unavailable_without_writes(self):
        q=self.f.queue;original=q.path
        wrong=self.f.root/'wrong-stage-schema.sqlite'
        with closing(sqlite3.connect(wrong)) as db,db:db.execute('CREATE TABLE unrelated(value TEXT)')
        before=wrong.read_bytes();q.path=wrong
        try:
            with self.assertRaises(ResearchQueueError):q.state_stage_counts()
            self.assertEqual(before,wrong.read_bytes())
        finally:q.path=original
        with q._db() as db:db.execute("UPDATE research_queue_namespace SET namespace='UNKNOWN'")
        before=q.path.read_bytes()
        with self.assertRaises(ResearchQueueError):q.state_stage_counts()
        self.assertEqual(before,q.path.read_bytes())
