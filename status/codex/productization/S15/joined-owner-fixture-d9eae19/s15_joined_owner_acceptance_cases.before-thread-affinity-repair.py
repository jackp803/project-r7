"""Joined real owners on one canonical store; accelerated FIXTURE only.

Catches broken intake/research lineage, unauthorized promotion after a genuine
quantitative loss, tampered sealed inputs, inferred fills and false cloud ACKs.
No native worker, browser, real forward, provider or financial admission claim.
"""
from contextlib import ExitStack,contextmanager
from datetime import timedelta
from decimal import Decimal
import json,unittest

from fastapi.testclient import TestClient
from application.cloud.bridge_transport import RcloneCloudTransport
from application.cloud.protocol import CloudError
from application.control_api.app import create_app
from application.control_api.owner_services import OwnerControlServices
from application.control_api.paper_ports import PaperReadControlPort,PaperStartControlPort
from application.intake.service import StrategyInboxService
from application.paper.service import PaperService,PaperMarketEvent
from application.paper.assessment import assess_forward
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from registry import StrategyIdentity,EvidenceGateError
from registry.operational_authority import ReleaseBinding,ProductLifecycleComposition,HumanAuthenticator
from storage.platform import open_sqlite_platform
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from storage.paper_feedback import PaperFeedbackOutbox
from strategy.v02.capabilities import _revision,build_capability_snapshot
from tests.product.test_api_owner_services import APIOwnerServicesTests
from tests.product.test_paper_runtime_v02 import simulation_fixture
from tests.application.test_cloud_bridge import CloudBridgeTests
from tests.application.test_product_assessment_binding import risk_fixture
from tests.application.test_research_robustness import selected
from tests.validation.robustness_fixtures import subject
from tests.validation.test_paper_promotion_policy import policy_fixture

class JoinedOwnerAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.h=APIOwnerServicesTests(methodName='test_actual_async_research_reaches_candidate_and_api_reports_owner_lineage')
        self.addCleanup(lambda:self.assertTrue(self.h.doCleanups(),'Actual API owner cleanup failed'))
        self.h.setUp()
        self.c=CloudBridgeTests(methodName='test_configuration_reference_is_metadata_only_and_package_flags_are_rejected')
        self.addCleanup(lambda:self.assertTrue(self.c.doCleanups(),'Local fake bridge cleanup failed'))
        self.c.setUp()
        # Copy only public fixture author payloads to the local fake remote.
        for path in self.h.cloud.rglob('*'):
            if path.is_file() and path.name!='.r7-root.json':
                destination=self.c.remote/path.relative_to(self.h.cloud)
                destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(path.read_bytes())
        self.bridge=self.c.bridge();self.transport=RcloneCloudTransport(self.bridge)
        h=self.h
        @contextmanager
        def inbox():
            with h.intake_factory() as intake,h.registry_factory() as e6:
                yield StrategyInboxService(self.transport,intake,e6,snapshot_root=h.snapshots,
                    owner_id='joined-fixture-scan',capability_snapshot_hash=build_capability_snapshot().snapshot_hash)
        self.inbox=inbox;self.login_sequence=0
        self.install_api()
        self.identity=StrategyIdentity(subject()['strategy_id'],subject()['strategy_version'])
        self.initial_now=h.clock[0]
    def install_api(self,reader=None,start=None):
        h=self.h
        owners=OwnerControlServices(h.config,namespace='FIXTURE',clock=lambda:h.clock[0],registry_factory=h.registry_factory,
            intake_factory=h.intake_factory,inbox_factory=self.inbox,research_queue=h.queue,
            research_resolver=h.owners.resolver,paper_reader=reader,paper_start=start)
        h.client.close()
        h.client=TestClient(create_app(h.config,auth=h.auth,commands=h.ledger,services=owners),
            base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000),raise_server_exceptions=False)
        self.addCleanup(h.client.close);self.login_sequence+=1
        h.login(command_id='joined-login-'+str(self.login_sequence))
    def research(self):
        staged=self.bridge.pull_once();self.assertEqual(staged['status'],'LOCAL_STAGED')
        self.assertGreater(staged['files_staged'],0)
        response=self.h.enqueue();job_id=response.json()['effect_ref'].removeprefix('research-job:')
        claim=self.h.queue.claim_next();self.assertEqual(claim.run_id,job_id)
        result=self.h.queue.step(claim.run_id,claim.generation)
        self.assertEqual(result['state'],'COMPLETE')
        view=self.h.client.get('/api/v1/research/runs/'+job_id).json()['data']['payload']
        self.assertEqual(view['owner_run_id'],view['outcome']['run_id'])
        self.assertEqual(view['evidence']['provenance']['provider_requests'],0)
        self.assertIsNone(self.h.queue.claim_next())
        return job_id,view
    def compose_paper(self):
        h=self.h;stack=ExitStack();self.addCleanup(stack.close)
        with h.registry_factory() as e6:product=e6.candidate_product_assessment(self.identity)
        self.assertEqual(product.namespace,'FIXTURE');self.assertEqual(product.status,'PASS')
        self.release=ReleaseBinding(namespace='FIXTURE',implementation_hash=_revision(),
            executable_revision=self.h.queue.evidence_view(self.job_id)['provenance']['executable_revision'],
            build_hash='sha256:'+'1'*64,config_hash='sha256:'+'2'*64,config_generation=1,
            capability_hash=build_capability_snapshot().snapshot_hash,provider_profile_hash='sha256:'+'3'*64,
            provider_ref='fixture-paper',account_ref='fixture-account',risk_policy_hash=product.risk_policy_hash,
            risk_generation=1,runtime_generation=1,release_kind='FIXTURE')
        promotion=policy_fixture();promotion.update(generation=2,min_elapsed_seconds=2,min_closed_trades=1,required_healthy_seconds=1)
        boundary=ProductLifecycleComposition(namespace='FIXTURE',current_release=lambda:self.release,
            resolve_evidence=lambda *args:None,authenticator=HumanAuthenticator(namespace='FIXTURE',reauth_seconds=300,
                verifier=lambda proof:None,clock=lambda:h.clock[0]),clock=lambda:h.clock[0])
        boundary.select_paper_policy('joined-fixture-short',promotion)
        # Intake/research, registry, process, canonical graph and feedback all
        # use the SAME fixture canonical.sqlite; no candidate/evidence copying.
        self.registry=stack.enter_context(open_sqlite_platform(h.config.database_path,research_namespace='FIXTURE',lifecycle_boundary=boundary))
        self.process=stack.enter_context(open_paper_process_journal(h.config.database_path))
        self.canonical=stack.enter_context(open_paper_runtime_journal(h.config.database_path))
        self.paper=PaperService(registry=self.registry,process_journal=self.process,canonical_journal=self.canonical,
            namespace='FIXTURE',simulation_policy=simulation_fixture(),risk_policy=risk_fixture(),promotion_policy=promotion,
            paper_policy_ref='joined-fixture-short',actor='joined-fixture-paper',workflow_authorized=True,
            submission_validity={'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}},
            current_release=lambda:self.release,clock=lambda:h.clock[0])
        boundary._resolve=self.paper.resolve_owner_evidence
        @contextmanager
        def factory():yield self.paper
        reader=PaperReadControlPort(namespace='FIXTURE',process_factory=lambda:open_paper_process_journal(h.config.database_path),
            canonical_factory=lambda:open_paper_runtime_journal(h.config.database_path),clock=lambda:h.clock[0])
        self.install_api(reader,PaperStartControlPort(namespace='FIXTURE',service_factory=factory))
    def event(self,seconds,price='60000',bars=False):
        now=self.initial_now+timedelta(seconds=seconds);self.h.clock[0]=now
        snapshot=MarketSnapshot('contracts-v0.1','BTC_USDT_PERP',now,now,'HEALTHY','EXPLICIT_FIXTURE',last_price=Decimal(price),freshness_ms=0)
        candles=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','1h',self.initial_now-timedelta(hours=2-index),
            self.initial_now-timedelta(hours=1-index),Decimal(value),Decimal(value)+1,Decimal(value)-1,Decimal(value),Decimal('1'),
            True,'EXPLICIT_FIXTURE',received_at=self.initial_now) for index,value in enumerate(('59000','60000'))) if bars else ()
        return PaperMarketEvent(snapshot,candles,'FIXTURE')
    def test_joined_cloud_intake_research_paper_ready_api_and_exact_feedback_ack(self):
        self.job_id,view=self.research()
        self.assertEqual(view['outcome']['strategy_lifecycle'],'CANDIDATE');self.assertEqual(view['evidence']['sealed_oos'],'PASS')
        self.compose_paper();h=self.h
        before=self.registry.get_strategy(self.identity)
        body=dict(command_id='joined-paper-start',expected_revision=before.registry_revision,
            strategy_id=self.identity.strategy_id,strategy_version=self.identity.strategy_version,policy_id='joined-fixture-short')
        started=h.post('/api/v1/paper/runs',body);self.assertEqual(started.status_code,200,started.text)
        self.assertEqual(started.json(),h.post('/api/v1/paper/runs',body).json())
        run_id=started.json()['effect_ref'].removeprefix('paper:')
        self.assertEqual(self.process.recover(run_id).process_generation,0)
        runtime=self.paper.runtime(run_id)
        self.assertEqual(runtime.on_market_event(self.event(0,bars=True)).status,'ACKNOWLEDGED')
        ack=h.client.get('/api/v1/paper/runs/'+run_id).json()['data']['payload']
        self.assertIsNone(ack['position']);self.assertEqual(ack['orders'][0]['actual_filled_quantity'],'0')
        self.assertEqual(runtime.on_market_event(self.event(1)).status,'PROTECTED')
        filled=h.client.get('/api/v1/paper/runs/'+run_id).json()['data']['payload']
        entry=next(row for row in filled['orders'] if row['client_order_id']==filled['entry_request']['client_order_id'])
        self.assertEqual(entry['original_ack_status'],'OPEN');self.assertEqual(entry['current_status'],'FILLED')
        self.assertEqual(entry['actual_filled_quantity'],'0.001')
        position=self.process.recover(run_id).state['runtime']['position']
        exit_result=runtime.on_market_event(self.event(2,'60020'))
        self.assertEqual(exit_result.status,'EXIT_REQUESTED');self.assertIn('E5_TARGET_REACHED',exit_result.reason_codes)
        self.assertEqual(runtime.on_market_event(self.event(3,'60020')).status,'CLOSED')
        graph=self.canonical.recover(position_id=position['position_id'])
        self.assertEqual(graph.status,'READY');self.assertEqual(graph.current_position_projection.payload['lifecycle_state'],'CLOSED')
        trade=self.process.recover(run_id).state['runtime']['closed_trades'][0]
        self.assertEqual(graph.trade_result.payload,trade);self.assertEqual(len(graph.fills),2)
        self.assertGreater(Decimal(trade['net_pnl']),0)
        assessment=assess_forward(runtime,self.paper.promotion).as_dict()
        self.assertEqual(assessment['status'],'PASS');self.assertEqual(assessment['actual_elapsed_seconds'],0)
        ready=self.paper.mark_ready(run_id,expected_revision=self.registry.get_strategy(self.identity).registry_revision,command_id='joined-ready')
        self.assertEqual(ready.current_lifecycle_state,'READY_FOR_APPROVAL')
        actual=h.client.get('/api/v1/strategies/'+self.identity.strategy_id+'/'+self.identity.strategy_version).json()['data']['payload']
        self.assertEqual(actual['current_lifecycle_state'],'READY_FOR_APPROVAL')
        metrics=h.client.get('/api/v1/paper/runs/'+run_id).json()['data']['payload']['metrics']
        self.assertEqual(metrics['total_trades'],1);self.assertEqual(Decimal(metrics['net_pnl']),Decimal(trade['net_pnl']))
        outbox=PaperFeedbackOutbox(self.process);operation=outbox.queue(runtime)
        expected=outbox.pending(1)[0][1];generation=self.process.recover(run_id).process_generation
        self.c.fake.outage=True
        self.assertEqual(outbox.flush(self.transport,limit=10).unavailable,1,'JOINED_CLOUD_OUTAGE_MUST_REMAIN_UNACKNOWLEDGED')
        self.assertEqual(outbox.publications()[0]['state'],'UNAVAILABLE')
        self.c.fake.outage=False
        self.assertEqual(outbox.flush(self.transport,limit=10).cloud_acknowledged,1)
        self.assertEqual(outbox.publications()[0]['operation_id'],operation)
        self.assertEqual(outbox.publications()[0]['state'],'CLOUD_ACKNOWLEDGED')
        for name,raw in expected.payloads.items():self.assertEqual((self.c.remote/expected.logical_path/name).read_bytes(),raw)
        feedback=json.loads(expected.payloads['feedback.json'])
        self.assertEqual(feedback['namespace'],'FIXTURE');self.assertEqual(feedback['observation']['actual_elapsed_seconds'],0)
        self.assertEqual(outbox.flush(self.transport,limit=10).attempted,0)
        self.assertEqual(self.process.recover(run_id).process_generation,generation)
    def test_joined_genuine_oos_loss_rejects_without_paper_run(self):
        def adverse(rows):
            for index,row in enumerate(rows[32:]):row.update(open=str(1000000+index),high=str(1000002+index),low=str(999999+index),close=str(1000001+index))
        selected(self.h.root,adverse)
        self.job_id,view=self.research()
        self.assertEqual(view['outcome']['strategy_lifecycle'],'REJECTED');self.assertEqual(view['evidence']['sealed_oos'],'FAIL')
        with self.h.queue.service_factory() as owner:report=owner.report(view['owner_run_id'])
        self.assertLess(Decimal(str(report['product_assessment']['sealed_backtest']['net_pnl'])),0)
        with self.h.registry_factory() as e6:
            self.assertEqual(e6.get_strategy(self.identity).current_lifecycle_state,'REJECTED')
            self.assertEqual(e6.list_accepted_paper_starts(limit=50,offset=0),[])
            with self.assertRaises(EvidenceGateError):e6.candidate_product_assessment(self.identity)
    def test_joined_changed_sealed_input_denies_queue_and_research_evidence(self):
        self.bridge.pull_once();self.h.scan()
        path=next(self.h.snapshots.glob('fixture-product-*'))/'strategy.json';path.write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(CloudError,'PAYLOAD_INTEGRITY_MISMATCH'):
            self.h.owners.resolver.resolve('fixture-product','selected-fixture')
        response=self.h.post('/api/v1/research/runs',dict(command_id='tampered-enqueue',expected_revision=1,
            submission_id='fixture-product',policy_id='selected-fixture'))
        self.assertNotEqual(response.status_code,202);self.assertEqual(self.h.queue.list(),[])
        self.assertFalse((self.h.root/'research.sqlite').exists())
        with self.h.registry_factory() as e6:
            self.assertEqual(e6.get_strategy(self.identity).current_lifecycle_state,'DRAFT')
            self.assertEqual(e6.list_accepted_paper_starts(limit=50,offset=0),[])
