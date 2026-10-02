from contextlib import contextmanager
import importlib.util
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from application.config import ProductConfig
from application.control_api.auth import LocalAuth
from application.control_api.commands import CommandLedger
from application.paper.service import PaperService
from storage.platform import open_sqlite_platform
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from registry.operational_authority import ProductLifecycleComposition
from tests.product import test_paper_runtime_v02 as fixtures
from tests.application.test_product_assessment_binding import risk_fixture
from tests.validation.test_paper_promotion_policy import policy_fixture


class APIPaperServicesTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('application.control_api.paper_ports'),
                             'Actual PAPER HTTP control ports are missing')
        from application.control_api.paper_ports import PaperReadControlPort, PaperStartControlPort
        from application.control_api.owner_services import OwnerControlServices
        from application.control_api.app import create_app
        self.h = fixtures.PaperRuntimeV02Tests(); self.h.setUp(); self.addCleanup(self.h.doCleanups)
        self.path = self.h.root/'paper-registry.sqlite'
        self.config = ProductConfig('r7-product-config-v0.2','fixture-paper-control',self.h.root,None,self.path)
        self.auth = LocalAuth(self.h.root/'auth.sqlite',namespace='FIXTURE',clock=lambda:self.h.clock[0])
        self.password='explicit-test-only-password-123'; self.auth.create_owner('local-owner',self.password)
        self.reader = PaperReadControlPort(namespace='FIXTURE',process_factory=lambda:open_paper_process_journal(self.h.root/'runtime.sqlite'),
            canonical_factory=lambda:open_paper_runtime_journal(self.h.root/'runtime.sqlite'),clock=lambda:self.h.clock[0])
        self.start_port = PaperStartControlPort(namespace='FIXTURE',service_factory=self.paper_factory)
        owners = OwnerControlServices(self.config,namespace='FIXTURE',clock=lambda:self.h.clock[0],
            registry_factory=lambda:open_sqlite_platform(self.path,research_namespace='FIXTURE'),paper_reader=self.reader,paper_start=self.start_port)
        app = create_app(self.config,auth=self.auth,commands=CommandLedger(self.h.root/'commands.sqlite',namespace='FIXTURE',clock=lambda:self.h.clock[0]),services=owners)
        self.client=TestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000),raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.headers={'Origin':'http://127.0.0.1:8765'}
        login=self.client.post('/api/v1/auth/login',json=dict(username='local-owner',password=self.password,command_id='login-one',expected_revision=0),headers=self.headers)
        self.assertEqual(login.status_code,200); self.headers['X-R7-CSRF']=login.json()['csrf_token']

    @contextmanager
    def paper_factory(self):
        boundary=ProductLifecycleComposition(namespace='FIXTURE',current_release=lambda:self.h.release[0],
            resolve_evidence=lambda *args:None,authenticator=self.h.boundary.authenticator,clock=lambda:self.h.clock[0])
        boundary.select_paper_policy('fixture-paper-policy',policy_fixture())
        with open_sqlite_platform(self.path,research_namespace='FIXTURE',lifecycle_boundary=boundary) as registry, \
                open_paper_process_journal(self.h.root/'runtime.sqlite') as process, open_paper_runtime_journal(self.h.root/'runtime.sqlite') as canonical:
            service=PaperService(registry=registry,process_journal=process,canonical_journal=canonical,namespace='FIXTURE',
                simulation_policy=fixtures.simulation_fixture(),risk_policy=risk_fixture(),promotion_policy=policy_fixture(),
                paper_policy_ref='fixture-paper-policy',actor='fixture-paper-runtime',workflow_authorized=True,
                submission_validity={'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}},
                current_release=lambda:self.h.release[0],clock=lambda:self.h.clock[0])
            boundary._resolve=service.resolve_owner_evidence
            yield service

    def api_start(self):
        before=self.h.registry.get_strategy(self.h.identity)
        body=dict(command_id='api-paper-start',expected_revision=before.registry_revision,strategy_id=self.h.identity.strategy_id,
            strategy_version=self.h.identity.strategy_version,policy_id='fixture-paper-policy')
        response=self.client.post('/api/v1/paper/runs',json=body,headers=self.headers)
        self.assertEqual(response.status_code,200,response.text)
        return response,body,response.json()['effect_ref'].removeprefix('paper:')

    def test_actual_start_persists_e6_run_once_without_attaching_or_replacing_runtime(self):
        response,body,run_id=self.api_start()
        recovered=self.h.process.recover(run_id)
        self.assertEqual(recovered.process_generation,0)
        self.assertEqual(recovered.binding['namespace'],'FIXTURE')
        self.assertEqual(self.h.registry.get_strategy(self.h.identity).current_lifecycle_state,'PAPER')
        self.assertEqual(response.json(),self.client.post('/api/v1/paper/runs',json=body,headers=self.headers).json())
        view=self.client.get('/api/v1/paper/runs/'+run_id)
        self.assertEqual(view.status_code,200,view.text)
        self.assertEqual(view.json()['data']['payload']['runtime_status'],'NOT_STARTED')
        self.assertIsNone(view.json()['data']['payload']['metrics'])
        self.assertIsNone(view.json()['data']['payload']['position'])

    def test_actual_pause_api_denies_entries_and_retains_worker_generation_and_protection(self):
        _,_,run_id=self.api_start()
        runtime=self.h.service.runtime(run_id)
        runtime.on_market_event(self.h.event(0,bars=True)); runtime.on_market_event(self.h.event(1))
        generation=self.h.process.recover(run_id).process_generation
        view=self.client.get('/api/v1/paper/runs/'+run_id).json()['data']
        response=self.client.post('/api/v1/paper/runs/'+run_id+'/pause',json=dict(command_id='api-pause',expected_revision=view['revision']),headers=self.headers)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'PAUSED')
        self.assertEqual(self.h.process.recover(run_id).process_generation,generation)
        self.assertTrue(self.h.process.entry_pause_requested(run_id))
        projection=self.h.process.recover(run_id).state['runtime']['position']
        self.assertEqual(projection['lifecycle_state'],'OPEN_PROTECTED')
        self.assertEqual(projection['actual_quantity'],'0.001')
        read=self.client.get('/api/v1/paper/runs/'+run_id).json()
        self.assertEqual(read['metadata']['current_or_last_known'],'LAST_KNOWN_GOOD')
        self.assertEqual(read['metadata']['as_of'],projection['broker_state_observed_at'])

    def test_wrong_selected_policy_or_stale_revision_cannot_create_runtime_or_paper(self):
        before=self.h.registry.get_strategy(self.h.identity)
        body=dict(command_id='wrong-policy',expected_revision=before.registry_revision,strategy_id=self.h.identity.strategy_id,
            strategy_version=self.h.identity.strategy_version,policy_id='wrong-selection')
        response=self.client.post('/api/v1/paper/runs',json=body,headers=self.headers)
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(self.h.registry.get_strategy(self.h.identity).current_lifecycle_state,'CANDIDATE')

    def test_readonly_paper_metrics_use_actual_published_e5_results_and_e3_costs(self):
        _,_,run_id=self.api_start(); runtime=self.h.service.runtime(run_id)
        runtime.on_market_event(self.h.event(0,bars=True)); runtime.on_market_event(self.h.event(1))
        runtime.on_market_event(self.h.event(2,'60020')); runtime.on_market_event(self.h.event(3,'60020'))
        source=self.h.process.recover(run_id); trade=source.state['runtime']['closed_trades'][0]
        body=self.client.get('/api/v1/paper/runs/'+run_id).json()['data']['payload']
        self.assertIsNotNone(body['metrics'],'Completed canonical trades must have actual E3 metrics')
        self.assertEqual(body['metrics']['total_trades'],1)
        self.assertEqual(__import__('decimal').Decimal(body['metrics']['net_pnl']),__import__('decimal').Decimal(trade['net_pnl']))
        self.assertEqual(body['metrics']['total_slippage_cost'],'0')
        self.assertEqual(self.h.process.recover(run_id).process_generation,source.process_generation)

    def test_unknown_pause_ack_is_reconciled_under_same_owner_command_after_lease(self):
        from datetime import timedelta
        from storage.runtime_models import RuntimeValidationError
        _,_,run_id=self.api_start(); original=self.reader.pause; calls=[0]
        def lose_ack(*args):
            receipt=original(*args); calls[0]+=1
            if calls[0]==1: raise RuntimeValidationError('PAPER_DURABLE_WRITE_FAILED','fixture-private-error-detail')
            return receipt
        self.reader.pause=lose_ack
        body=dict(command_id='uncertain-pause',expected_revision=0)
        first=self.client.post('/api/v1/paper/runs/'+run_id+'/pause',json=body,headers=self.headers)
        self.assertEqual(first.status_code,503)
        self.assertNotIn('fixture-private-error-detail',first.text)
        self.h.clock[0]+=timedelta(seconds=31)
        recovered=self.client.post('/api/v1/paper/runs/'+run_id+'/pause',json=body,headers=self.headers)
        self.assertEqual(recovered.status_code,200,'Unknown owner outcome must reconcile rather than cache a false terminal failure')
        self.assertEqual(recovered.json()['status'],'PAUSED')
        self.assertEqual(self.h.process.control_revision(run_id),1)
        self.assertEqual(self.h.process.recover(run_id).process_generation,0)


if __name__=='__main__': unittest.main()
