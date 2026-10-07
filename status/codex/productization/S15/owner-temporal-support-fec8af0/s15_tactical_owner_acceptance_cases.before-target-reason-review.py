"""Actual owner tactical expiry composition; isolated accelerated FIXTURE only."""
from datetime import timedelta
import copy,json,unittest
from tests.product import test_paper_runtime_v02 as paper

class TacticalOwnerAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.h=paper.PaperRuntimeV02Tests(methodName='test_full_entry_ack_fill_verified_protection_target_exit_flat_result')
        self.addCleanup(self.cleanup_owner_fixture)
        self.h.setUp()
    def cleanup_owner_fixture(self):
        self.assertTrue(self.h.doCleanups(),'Actual owner fixture cleanup failed')
    def service(self,start=0,end=2):
        h=self.h
        value=dict(intent_class='TACTICAL_STRATEGY',validity={
            'from':(h.initial_now+timedelta(seconds=start)).isoformat().replace('+00:00','Z'),
            'until':(h.initial_now+timedelta(seconds=end)).isoformat().replace('+00:00','Z')})
        return h.service_type(registry=h.registry,process_journal=h.process,canonical_journal=h.canonical,
            namespace='FIXTURE',simulation_policy=paper.simulation_fixture(),risk_policy=paper.risk_fixture(),
            promotion_policy=paper.policy_fixture(),paper_policy_ref='fixture-paper-policy',
            actor='fixture-paper-runtime',workflow_authorized=True,submission_validity=value,
            current_release=lambda:h.release[0],clock=lambda:h.clock[0])
    def start(self,start=0,end=2):
        h=self.h;h.service=self.service(start,end);h.boundary._resolve=h.service.resolve_owner_evidence
        product=h.registry.candidate_product_assessment(h.identity)
        self.assertEqual('PASS',product.status)
        self.assertTrue(json.loads(product.payload_json)['independent_oos'])
        self.assertEqual('FIXTURE',product.namespace)
        return h.start()
    def state(self,run):return self.h.process.recover(run.run_id).state
    def test_expiry_boundary_denies_entry_after_actual_research_candidate_and_paper_gate(self):
        h=self.h;run=self.start()
        result=run.on_market_event(h.event(2,bars=True))
        self.assertEqual('BLOCKED',result.status);self.assertIn('SUBMISSION_EXPIRED',result.reason_codes)
        state=self.state(run)
        self.assertEqual([],state['broker']['payload']['submissions']);self.assertIsNone(state['runtime']['position'])
        self.assertEqual('PAPER',h.registry.get_strategy(h.identity).current_lifecycle_state)
        self.assertEqual([],state['runtime']['closed_trades'])
    def test_ack_is_cancelled_at_tactical_expiry_without_fill_or_plan_renewal(self):
        h=self.h;run=self.start(end=1)
        self.assertEqual('ACKNOWLEDGED',run.on_market_event(h.event(0,bars=True)).status)
        plan=copy.deepcopy(self.state(run)['runtime']['plan'])
        result=run.on_market_event(h.event(1))
        self.assertEqual('BLOCKED',result.status);self.assertIn('SUBMISSION_EXPIRED',result.reason_codes)
        state=self.state(run)
        self.assertEqual(plan,state['runtime']['plan']);self.assertIsNone(state['runtime']['position'])
        self.assertEqual('CANCELED',state['broker']['payload']['submissions'][0]['order']['result']['order_status'])
        self.assertEqual([],state['broker']['payload']['submissions'][0]['order']['fills'])
        run.on_market_event(h.event(2,bars=True))
        self.assertEqual(1,len(self.state(run)['broker']['payload']['submissions']))
    def test_expired_tactical_preserves_open_protection_and_e5_target_exit_flat_result(self):
        h=self.h;run=self.start()
        run.on_market_event(h.event(0,bars=True));self.assertEqual('PROTECTED',run.on_market_event(h.event(1)).status)
        before=copy.deepcopy(self.state(run)['runtime']);run.on_market_event(h.event(2))
        state=self.state(run)['runtime']
        self.assertEqual(before['protection_request'],state['protection_request'])
        self.assertEqual(before['position']['opened_at'],state['position']['opened_at'])
        self.assertEqual('OPEN_PROTECTED',state['position']['lifecycle_state'])
        stop=next(row for row in self.state(run)['broker']['payload']['submissions']
                  if row['request']['client_order_id']==state['protection_request']['client_order_id'])
        self.assertEqual('OPEN',stop['order']['result']['order_status'])
        self.assertEqual('EXIT_REQUESTED',run.on_market_event(h.event(3,'60020')).status)
        self.assertEqual('CLOSED',run.on_market_event(h.event(4,'60020')).status)
        state=self.state(run)['runtime'];self.assertEqual(1,len(state['closed_trades']))
        recovered=h.canonical.recover(position_id=state['position']['position_id'])
        self.assertEqual('READY',recovered.status);self.assertEqual(state['closed_trades'][0],recovered.trade_result.payload)
        self.assertEqual('CLOSED',recovered.current_position_projection.payload['lifecycle_state'])
    def test_expired_tactical_restart_preserves_binding_first_fill_balance_and_management(self):
        h=self.h;run=self.start()
        run.on_market_event(h.event(0,bars=True));run.on_market_event(h.event(1));h.event(2)
        before=h.process.recover(run.run_id);validity=h.service.validity_json
        restarted=self.service();h.boundary._resolve=restarted.resolve_owner_evidence
        resumed=restarted.runtime(run.run_id);after=h.process.recover(run.run_id)
        self.assertEqual(validity,restarted.validity_json);self.assertEqual(before.binding,after.binding)
        self.assertEqual(before.state,after.state);self.assertEqual(before.process_generation+1,after.process_generation)
        self.assertTrue(resumed.engine.reconciled)
        self.assertEqual('EXIT_REQUESTED',resumed.on_market_event(h.event(3,'60020')).status)
        self.assertEqual('CLOSED',resumed.on_market_event(h.event(4,'60020')).status)
        self.assertEqual(1,len(self.state(resumed)['runtime']['closed_trades']))
    def test_original_not_yet_valid_interval_can_enter_only_when_valid_then_manage_after_expiry(self):
        h=self.h;run=self.start(start=1,end=3)
        result=run.on_market_event(h.event(0,bars=True))
        self.assertEqual('BLOCKED',result.status);self.assertIn('SUBMISSION_NOT_YET_VALID',result.reason_codes)
        self.assertEqual([],self.state(run)['broker']['payload']['submissions'])
        self.assertEqual('ACKNOWLEDGED',run.on_market_event(h.event(1,bars=True)).status)
        self.assertEqual('PROTECTED',run.on_market_event(h.event(2)).status)
        self.assertEqual('EXIT_REQUESTED',run.on_market_event(h.event(3,'60020')).status)
        self.assertEqual('CLOSED',run.on_market_event(h.event(4,'60020')).status)
