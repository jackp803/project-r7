"""Actual E2/E5/E4/E6 accelerated PAPER mechanics; no real forward claim."""
from contextlib import ExitStack
from datetime import timedelta
from decimal import Decimal
import importlib.util
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from market_data.candle import Candle
from market_data.current import MarketSnapshot
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from tests.registry import test_operational_lifecycle_v02 as lifecycle
from tests.application.test_product_assessment_binding import risk_fixture
from tests.validation.test_paper_promotion_policy import policy_fixture


def simulation_fixture():
    return dict(schema_version='r7-paper-simulation-policy-v0.2', namespace='FIXTURE',
        mode='ACCELERATED_FIXTURE', policy_id='FIXTURE_SIMULATION', generation=1,
        initial_balance_usdt='1000', quantity='0.001', leverage='1',
        fee_rate='0.00005', slippage_bps='0', estimated_roundtrip_cost_usdt='0.006',
        initial_fill_fraction='1', partial_remainder_behavior='CANCEL_AFTER_FIRST_FILL',
        market_max_age_seconds=5, action_ttl_seconds=30, protection_poll_seconds=1,
        maximum_cached_candles_per_timeframe=2000, funding_model='EXPLICIT_REGISTERED_PAPER_ZERO',
        account_scope='ISOLATED_PER_STRATEGY_RUN')


class PaperRuntimeV02Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.service'),
                             'Continuous owner-composed PaperService is missing')
        from application.paper.service import PaperService, PaperMarketEvent
        self.event_type = PaperMarketEvent
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        helper = lifecycle.OperationalLifecycleTests()
        api, research, run_id, identity, boundary, auth, clock, release, envelope = helper.fixture(self.root)
        self.addCleanup(research.close)
        helper.run_id = run_id
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.registry = self.stack.enter_context(helper.platform(self.root, research, run_id, boundary, 'paper-registry'))
        helper.build(self.registry, identity, 'CANDIDATE', auth)
        self.identity, self.clock, self.release, self.boundary = identity, clock, release, boundary
        self.initial_now = clock[0]
        self.process = self.stack.enter_context(open_paper_process_journal(self.root/'runtime.sqlite'))
        self.canonical = self.stack.enter_context(open_paper_runtime_journal(self.root/'runtime.sqlite'))
        self.service_type = PaperService
        self.service = self.make_service(simulation_fixture())
        boundary._resolve = self.service.resolve_owner_evidence

    def make_service(self, simulation, *, promotion=None, paper_policy_ref='fixture-paper-policy'):
        return self.service_type(registry=self.registry, process_journal=self.process,
            canonical_journal=self.canonical, namespace='FIXTURE', simulation_policy=simulation,
            risk_policy=risk_fixture(), promotion_policy=policy_fixture() if promotion is None else promotion, paper_policy_ref=paper_policy_ref,
            actor='fixture-paper-runtime', workflow_authorized=True,
            submission_validity={'intent_class':'EVERGREEN_STRATEGY','validity':{'from':None,'until':None}},
            current_release=lambda:self.release[0], clock=lambda:self.clock[0])

    def start(self):
        ref = self.service.start(self.identity, self.service.policy_ref,
            self.registry.get_strategy(self.identity).registry_revision, 'start-paper')
        self.assertEqual(self.registry.get_strategy(self.identity).current_lifecycle_state, 'PAPER')
        return self.service.runtime(ref.run_id)

    def event(self, seconds, price='60000', *, bars=False, stale=False):
        now = self.initial_now + timedelta(seconds=seconds); self.clock[0] = now
        observed = now - timedelta(seconds=10) if stale else now
        snapshot = MarketSnapshot('contracts-v0.1', 'BTC_USDT_PERP', observed, now,
            'HEALTHY', 'EXPLICIT_FIXTURE', last_price=Decimal(price), freshness_ms=10000 if stale else 0)
        candles = tuple(Candle('contracts-v0.1', 'BTC_USDT_PERP', '1h',
            self.initial_now-timedelta(hours=2-index), self.initial_now-timedelta(hours=1-index),
            Decimal(value), Decimal(value)+1, Decimal(value)-1, Decimal(value), Decimal('1'),
            True, 'EXPLICIT_FIXTURE', received_at=self.initial_now)
            for index,value in enumerate(('59000','60000'))) if bars else ()
        return self.event_type(snapshot=snapshot, candles=candles, source_kind='FIXTURE')

    def configure_next_simulated_submit(self,runtime,event,kind,*,role=None):
        import hashlib,json
        from application.paper.orchestrator import PaperCoordinator,PaperStep
        from brokers.paper_state import canonical_state_json
        request=dict(kind='MARKET',snapshot=event.snapshot.to_interchange_dict(),
            candles=[row.to_interchange_dict() for row in event.candles],source_kind=event.source_kind)
        predicted=runtime.engine.produce(self.process.recover(runtime.run_id).state,request,self.clock[0])
        order=predicted.state['runtime']['protection_request'] if role=='PROTECTION_STOP' else predicted.state['runtime']['entry_request']
        def configure(state,request,now):
            payload=state['broker']['payload']
            if kind=='REJECTED': payload['rejected_outcomes'][order['client_order_id']]='FIXTURE_SUBMIT_REJECTED'
            else: payload['ambiguous_outcomes'][order['client_order_id']]=False
            state['broker']['payload_hash']=hashlib.sha256(canonical_state_json(payload).encode()).hexdigest()
            return PaperStep(state,[],'HOLD',())
        PaperCoordinator(self.process,self.canonical,runtime.run_id,runtime.coordinator.generation,
            configure,clock=lambda:self.clock[0]).execute('fixture-control-'+kind+'-'+str(role),dict(kind='FIXTURE_SIMULATION_CONFIG'))

    def test_full_entry_ack_fill_verified_protection_target_exit_flat_result(self):
        runtime = self.start()
        ack = runtime.on_market_event(self.event(0, bars=True))
        self.assertEqual(ack.status, 'ACKNOWLEDGED')
        self.assertIsNone(self.process.recover(runtime.run_id).state['runtime']['position'])
        protected = runtime.on_market_event(self.event(1))
        self.assertEqual(protected.status, 'PROTECTED')
        position = self.process.recover(runtime.run_id).state['runtime']['position']
        self.assertEqual(position['lifecycle_state'], 'OPEN_PROTECTED')
        requested = runtime.on_market_event(self.event(2, '60020'))
        self.assertEqual(requested.status, 'EXIT_REQUESTED')
        pending = self.process.recover(runtime.run_id).state['runtime']['position']
        self.assertEqual(pending['lifecycle_state'], 'EXIT_REQUESTED')
        self.assertEqual(pending['actual_quantity'], '0.001')
        closed = runtime.on_market_event(self.event(3, '60020'))
        self.assertEqual(closed.status, 'CLOSED')
        state = self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(len(state['closed_trades']), 1)
        result = state['closed_trades'][0]
        self.assertGreater(Decimal(result['net_pnl']), 0)
        recovered = self.canonical.recover(position_id=position['position_id'])
        self.assertEqual(recovered.status, 'READY')
        self.assertEqual(recovered.current_position_projection.payload['lifecycle_state'], 'CLOSED')
        self.assertEqual(len(recovered.fills), 2)
        self.assertEqual(recovered.trade_result.payload, result)

    def test_duplicate_finalized_boundary_does_not_create_a_second_logical_entry(self):
        runtime = self.start(); event = self.event(0, bars=True)
        first = runtime.on_market_event(event)
        second = runtime.on_market_event(event)
        self.assertEqual(first, second)
        state = self.process.recover(runtime.run_id).state
        self.assertEqual(len(state['broker']['payload']['submissions']), 1)
        self.assertEqual(self.process.recover(runtime.run_id).revision, 1)

    def test_actual_broker_readback_advances_observation_without_renewing_first_fill(self):
        runtime = self.start()
        runtime.on_market_event(self.event(0, bars=True))
        runtime.on_market_event(self.event(1))
        original = self.process.recover(runtime.run_id).state['runtime']['position']
        runtime.on_market_event(self.event(2))
        current = self.process.recover(runtime.run_id).state['runtime']['position']
        self.assertEqual(current['opened_at'], original['opened_at'])
        self.assertEqual(current['actual_quantity'], original['actual_quantity'])
        self.assertEqual(current['broker_state_observed_at'], '2026-10-03T00:00:02Z')
        self.assertEqual(current['lifecycle_state'], 'OPEN_PROTECTED')
        self.assertEqual(self.canonical.recover(position_id=current['position_id']).status, 'READY')

    def test_stale_market_admits_no_order_and_reports_observed_reason(self):
        runtime = self.start()
        outcome = runtime.on_market_event(self.event(0, bars=True, stale=True))
        self.assertEqual(outcome.status, 'BLOCKED')
        self.assertIn('MARKET_STALE', outcome.reason_codes)
        self.assertEqual(self.process.recover(runtime.run_id).state['broker']['payload']['submissions'], [])

    def test_retirement_blocks_new_entries_and_preserves_existing_management(self):
        runtime = self.start()
        runtime.on_market_event(self.event(0, bars=True))
        runtime.on_market_event(self.event(1))
        self.registry.retire(self.identity, actor='fixture-owner', reason_codes=('USER_RETIRED',))
        self.assertEqual(runtime.on_market_event(self.event(2, '60020')).status, 'EXIT_REQUESTED')
        closed = runtime.on_market_event(self.event(3, '60020'))
        self.assertEqual(closed.status, 'CLOSED')
        self.assertEqual(self.registry.get_strategy(self.identity).current_lifecycle_state, 'RETIRED')
        self.assertEqual(len(self.process.recover(runtime.run_id).state['runtime']['closed_trades']), 1)

    def test_partial_fill_cancels_remainder_before_protecting_actual_quantity(self):
        config = simulation_fixture(); config['initial_fill_fraction'] = '0.5'
        self.service = self.make_service(config); self.boundary._resolve = self.service.resolve_owner_evidence
        runtime = self.start()
        runtime.on_market_event(self.event(0, bars=True))
        self.assertEqual(runtime.on_market_event(self.event(1)).status, 'PROTECTED')
        state = self.process.recover(runtime.run_id).state
        position = state['runtime']['position']
        self.assertEqual(Decimal(position['actual_quantity']), Decimal('0.0005'))
        from brokers.paper import PaperBroker
        broker = PaperBroker.from_state(state['broker'])
        request = state['runtime']['entry_request']
        self.assertEqual(broker.query_order(request['client_order_id']).order_status.value, 'CANCELED')
        self.assertEqual(Decimal(state['runtime']['protection_request']['quantity']), Decimal('0.0005'))
        runtime.on_market_event(self.event(2, '60020'))
        self.assertEqual(runtime.on_market_event(self.event(3, '60020')).status, 'CLOSED')
        self.assertEqual(broker.query_position('BTC_USDT_PERP').net_quantity, Decimal('0.0005'))
        flat = PaperBroker.from_state(self.process.recover(runtime.run_id).state['broker'])
        self.assertEqual(flat.query_position('BTC_USDT_PERP').net_quantity, 0)

    def test_entry_expiry_cancels_unfilled_order_without_renewing_plan(self):
        runtime = self.start(); runtime.on_market_event(self.event(0, bars=True))
        original = self.process.recover(runtime.run_id).state['runtime']['plan']
        outcome = runtime.on_market_event(self.event(31))
        self.assertEqual(outcome.status, 'EXPIRED')
        state = self.process.recover(runtime.run_id).state
        self.assertEqual(state['runtime']['plan'], original)
        self.assertIsNone(state['runtime']['position'])
        self.assertEqual(state['broker']['payload']['submissions'][0]['order']['result']['order_status'], 'CANCELED')
        self.assertEqual(state['broker']['payload']['submissions'][0]['order']['fills'], [])

    def test_max_hold_deadline_management_does_not_wait_for_new_entry_bar(self):
        runtime = self.start(); runtime.on_market_event(self.event(0, bars=True))
        runtime.on_market_event(self.event(1))
        self.clock[0] = self.initial_now + timedelta(seconds=3601)
        outcome = runtime.on_deadline(self.clock[0])
        self.assertEqual(outcome.status, 'EXIT_REQUESTED')
        state = self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(state['exit_action']['reason_codes'], ['E5_MAX_HOLD_REACHED'])
        self.assertEqual(state['position']['actual_quantity'], '0.001')
        self.assertEqual(state['last_entry_boundary'], '2026-10-03T00:00:00Z')
        self.assertEqual(runtime.on_market_event(self.event(3602)).status, 'CLOSED')

    def test_pause_preserves_open_protection_and_management(self):
        runtime = self.start(); runtime.on_market_event(self.event(0, bars=True))
        runtime.on_market_event(self.event(1))
        protected = self.process.recover(runtime.run_id).state['runtime']['protection_request']
        self.clock[0] = self.initial_now + timedelta(seconds=2)
        self.service.stop_new_entries(runtime.run_id, 'pause-1')
        state = self.process.recover(runtime.run_id).state
        self.assertFalse(state['runtime']['paper_entries_allowed'])
        self.assertEqual(state['runtime']['protection_request'], protected)
        stop = next(row for row in state['broker']['payload']['submissions'] if row['request']['client_order_id']==protected['client_order_id'])
        self.assertEqual(stop['order']['result']['order_status'], 'OPEN')
        runtime.on_market_event(self.event(3, '60020'))
        self.assertEqual(runtime.on_market_event(self.event(4, '60020')).status, 'CLOSED')

    def test_restart_reconciles_actual_history_and_does_not_reset_first_fill_or_balance(self):
        runtime = self.start(); runtime.on_market_event(self.event(0, bars=True))
        runtime.on_market_event(self.event(1))
        before = self.process.recover(runtime.run_id)
        self.clock[0] = self.initial_now + timedelta(seconds=2)
        restarted_service = self.make_service(simulation_fixture())
        self.boundary._resolve = restarted_service.resolve_owner_evidence
        resumed = restarted_service.runtime(runtime.run_id)
        recovered = self.process.recover(runtime.run_id)
        self.assertEqual(recovered.state, before.state)
        self.assertEqual(recovered.process_generation, before.process_generation+1)
        self.assertTrue(resumed.engine.reconciled)
        resumed.on_market_event(self.event(3, '60020'))
        self.assertEqual(resumed.on_market_event(self.event(4, '60020')).status, 'CLOSED')
        self.assertEqual(len(self.process.recover(runtime.run_id).state['runtime']['closed_trades']), 1)

    def test_authoritative_protection_loss_requests_e5_emergency_exit_and_closes_later(self):
        from brokers.paper import PaperBroker
        from brokers.paper_state import encode_fact
        from application.paper.orchestrator import PaperCoordinator, PaperStep
        runtime = self.start(); runtime.on_market_event(self.event(0, bars=True))
        runtime.on_market_event(self.event(1)); self.event(2)
        def cancel_actual_protection(state, request, now):
            broker = PaperBroker.from_state(state['broker'])
            stop = state['runtime']['protection_request']
            result = broker.cancel_order(stop['client_order_id'], observed_at=now)
            return PaperStep(dict(broker=broker.export_state(), runtime=state['runtime']),
                [dict(kind='ORDER_RESULT',payload=encode_fact(result))], 'HOLD', ())
        PaperCoordinator(self.process,self.canonical,runtime.run_id,runtime.coordinator.generation,
            cancel_actual_protection,clock=lambda:self.clock[0]).execute('fixture-stop-canceled',dict(kind='FIXTURE_OWNER_FAULT'))
        outcome = runtime.on_market_event(self.event(3))
        self.assertEqual(outcome.status, 'EXIT_REQUESTED')
        state = self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(state['exit_source_position']['lifecycle_state'], 'EMERGENCY')
        self.assertEqual(state['exit_request']['order_role'], 'EMERGENCY_EXIT')
        self.assertEqual(runtime.on_market_event(self.event(4)).status, 'CLOSED')
        self.assertEqual(self.canonical.recover(position_id=state['position']['position_id']).status, 'READY')

    def test_stop_trigger_reduces_with_original_verified_protection_order(self):
        runtime = self.start(); runtime.on_market_event(self.event(0, bars=True))
        runtime.on_market_event(self.event(1))
        stop = self.process.recover(runtime.run_id).state['runtime']['protection_request']
        outcome = runtime.on_market_event(self.event(2, '59989'))
        self.assertEqual(outcome.status, 'EXIT_REQUESTED')
        self.assertIn('PROTECTION_TRIGGER_OBSERVED', outcome.reason_codes)
        pending = self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(pending['exit_request']['client_order_id'], stop['client_order_id'])
        self.assertEqual(runtime.on_market_event(self.event(3, '59989')).status, 'CLOSED')
        result = self.process.recover(runtime.run_id).state['runtime']['closed_trades'][0]
        self.assertLess(Decimal(result['net_pnl']), 0)
        self.assertEqual(result['exit_order_request_ids'], [stop['order_request_id']])

    def test_scheduler_runs_due_management_without_market_or_entry_candle(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.scheduler'), 'Bounded independent deadline scheduler missing')
        from application.paper.scheduler import PaperScheduler
        runtime = self.start(); runtime.on_market_event(self.event(0, bars=True))
        runtime.on_market_event(self.event(1))
        scheduler = PaperScheduler(runtime,maximum_pending_events=2)
        self.clock[0] = self.initial_now+timedelta(seconds=3601)
        outcomes = scheduler.tick()
        self.assertTrue(any(row.status=='EXIT_REQUESTED' for row in outcomes))
        state = self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(state['exit_action']['reason_codes'], ['E5_MAX_HOLD_REACHED'])
        revision = self.process.recover(runtime.run_id).revision
        scheduler.tick()
        self.assertEqual(self.process.recover(runtime.run_id).revision,revision)
        self.assertLessEqual(scheduler.next_wait_seconds(),1)

    def test_scheduler_bounds_acquisition_queue_and_processes_management_first(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.scheduler'), 'Bounded market queue missing')
        from application.paper.scheduler import PaperScheduler
        runtime = self.start(); scheduler = PaperScheduler(runtime,maximum_pending_events=2)
        first = self.event(0,bars=True); second = self.event(1); third = self.event(2)
        self.assertTrue(scheduler.submit_event(first)); self.assertTrue(scheduler.submit_event(second))
        self.assertFalse(scheduler.submit_event(third))
        outcomes = scheduler.tick()
        self.assertEqual(outcomes[0].status,'BLOCKED')
        self.assertEqual(outcomes[0].reason_codes,('MARKET_NOT_CONNECTED',))
        self.assertEqual(outcomes[1].status,'ACKNOWLEDGED')
        self.assertEqual(scheduler.pending_events,1)

    def test_accelerated_forward_assessment_never_counts_simulated_time_as_real_elapsed(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.assessment'), 'Actual bound forward assessment missing')
        from application.paper.assessment import assess_forward
        runtime = self.start(); runtime.on_market_event(self.event(0,bars=True))
        runtime.on_market_event(self.event(1)); runtime.on_market_event(self.event(2,'60020'))
        runtime.on_market_event(self.event(3,'60020')); self.event(3601)
        runtime.on_deadline(self.clock[0])
        assessment = assess_forward(runtime,self.service.promotion)
        body = assessment.as_dict()
        self.assertEqual(body['forward_mode'],'ACCELERATED_FIXTURE')
        self.assertEqual(body['actual_elapsed_seconds'],0)
        self.assertEqual(body['closed_trades'],1)
        self.assertEqual(body['status'],'BLOCKED')
        self.assertIn('INSUFFICIENT_CLOSED_TRADES',body['reason_codes'])
        self.assertGreaterEqual(body['simulated_elapsed_seconds'],3601)

    def test_unfinalized_event_rejected_without_poisoning_durable_operation_queue(self):
        runtime = self.start(); event=self.event(0,bars=True)
        changed=replace(event,candles=(replace(event.candles[-1],is_closed=False),))
        with self.assertRaises(ValueError): runtime.on_market_event(changed)
        self.assertEqual(self.process.recover(runtime.run_id).pending_operations,())
        self.assertEqual(runtime.on_market_event(event).status,'ACKNOWLEDGED')

    def test_future_deadline_rejected_without_creating_an_operation(self):
        runtime = self.start()
        with self.assertRaises(ValueError): runtime.on_deadline(self.initial_now+timedelta(hours=4))
        self.assertEqual(self.process.recover(runtime.run_id).revision,0)
        self.assertEqual(self.process.recover(runtime.run_id).pending_operations,())

    def test_forward_policy_change_cannot_reuse_previous_run_as_promotion_evidence(self):
        from application.paper.assessment import assess_forward
        from validation.paper_policy import parse_paper_promotion_policy
        from registry import EvidenceGateError
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True))
        changed=policy_fixture(); changed['generation']=2
        with self.assertRaises(EvidenceGateError):
            assess_forward(runtime,parse_paper_promotion_policy(changed,namespace='FIXTURE'))

    def test_fixture_readiness_requires_actual_bound_forward_assessment(self):
        self.assertTrue(hasattr(self.service,'mark_ready'),'Actual bound forward readiness service missing')
        small=policy_fixture(); small.update(generation=2,min_elapsed_seconds=2,min_closed_trades=1,required_healthy_seconds=1)
        self.boundary.select_paper_policy('fixture-paper-policy-short',small)
        self.service=self.make_service(simulation_fixture(),promotion=small,paper_policy_ref='fixture-paper-policy-short')
        self.boundary._resolve=self.service.resolve_owner_evidence
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True))
        runtime.on_market_event(self.event(1)); runtime.on_market_event(self.event(2,'60020'))
        runtime.on_market_event(self.event(3,'60020')); runtime.on_market_event(self.event(4,'60020'))
        current=self.registry.get_strategy(self.identity)
        self.service.mark_ready(runtime.run_id,expected_revision=current.registry_revision,command_id='fixture-ready')
        self.assertEqual(self.registry.get_strategy(self.identity).current_lifecycle_state,'READY_FOR_APPROVAL')

    def test_full_fill_checkpoint_recovers_publication_without_replaying_fill(self):
        from application.paper.orchestrator import PaperCoordinator
        from brokers.paper import PaperBroker
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True))
        with patch.object(PaperCoordinator,'_publish',side_effect=RuntimeError('injected publication interruption')):
            with self.assertRaises(RuntimeError): runtime.on_market_event(self.event(1))
        before=self.process.recover(runtime.run_id)
        self.assertEqual(before.state['runtime']['position']['lifecycle_state'],'OPEN_PROTECTED')
        self.assertEqual(len(before.pending_operations),1)
        resumed_service=self.make_service(simulation_fixture()); self.boundary._resolve=resumed_service.resolve_owner_evidence
        self.clock[0]=self.initial_now+timedelta(seconds=2)
        resumed=resumed_service.runtime(runtime.run_id)
        after=self.process.recover(runtime.run_id)
        self.assertEqual(after.state,before.state); self.assertEqual(after.pending_operations,())
        self.assertTrue(resumed.engine.reconciled)
        broker=PaperBroker.from_state(after.state['broker'])
        entry=after.state['runtime']['entry_request']
        self.assertEqual(len(broker.query_fills(entry['client_order_id'])),1)
        self.assertEqual(self.canonical.recover(position_id=after.state['runtime']['position']['position_id']).status,'READY')

    def test_actual_raw_position_effect_uses_canonical_owner_writer(self):
        from application.paper.orchestrator import PaperCoordinator,PaperStep
        from position.lifecycle_projection import _broker_fact_payload
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True)); runtime.on_market_event(self.event(1))
        position=self.process.recover(runtime.run_id).state['runtime']['position']
        raw=dict(_broker_fact_payload(position),lifecycle_state=position['lifecycle_state'])
        def observed(state,request,now):
            return PaperStep(state,[dict(kind='RAW_POSITION',payload=raw)],'HOLD',())
        PaperCoordinator(self.process,self.canonical,runtime.run_id,runtime.coordinator.generation,
            observed,clock=lambda:self.clock[0]).execute('raw-readback',dict(kind='ACTUAL_OWNER_OBSERVATION'))
        graph=self.canonical.recover(position_id=position['position_id'])
        self.assertEqual(len(graph.raw_position_observations),1)
        self.assertEqual(graph.raw_position_observations[0].payload,raw)

    def test_unresolved_entry_submit_blocks_without_retry_or_reset(self):
        runtime=self.start(); event=self.event(0,bars=True)
        self.configure_next_simulated_submit(runtime,event,'UNKNOWN')
        outcome=runtime.on_market_event(event)
        self.assertEqual(outcome.status,'BLOCKED')
        self.assertIn('ENTRY_SUBMIT_RECONCILIATION_REQUIRED',outcome.reason_codes)
        runtime.on_market_event(self.event(1))
        state=self.process.recover(runtime.run_id).state
        self.assertEqual(len(state['broker']['payload']['submissions']),1)
        self.assertIsNone(state['broker']['payload']['submissions'][0]['order'])
        self.assertIsNone(state['runtime']['position'])

    def test_rejected_initial_protection_enters_emergency_and_management_closes(self):
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True)); event=self.event(1)
        self.configure_next_simulated_submit(runtime,event,'REJECTED',role='PROTECTION_STOP')
        blocked=runtime.on_market_event(event)
        self.assertEqual(blocked.status,'BLOCKED')
        self.assertEqual(self.process.recover(runtime.run_id).state['runtime']['position']['lifecycle_state'],'EMERGENCY')
        self.assertEqual(runtime.on_market_event(self.event(2)).status,'EXIT_REQUESTED')
        self.assertEqual(runtime.on_market_event(self.event(3)).status,'CLOSED')

    def test_missing_initial_protection_remains_reconciliation_required_on_restart(self):
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True)); event=self.event(1)
        self.configure_next_simulated_submit(runtime,event,'UNKNOWN',role='PROTECTION_STOP')
        blocked=runtime.on_market_event(event)
        self.assertEqual(blocked.status,'BLOCKED')
        before=self.process.recover(runtime.run_id).state
        self.assertEqual(before['runtime']['position']['lifecycle_state'],'RECONCILIATION_REQUIRED')
        resumed_service=self.make_service(simulation_fixture()); self.boundary._resolve=resumed_service.resolve_owner_evidence
        resumed=resumed_service.runtime(runtime.run_id)
        outcome=resumed.on_market_event(self.event(2))
        self.assertEqual(outcome.status,'BLOCKED')
        self.assertIn('PROTECTION_RECONCILIATION_REQUIRED',outcome.reason_codes)
        after=self.process.recover(runtime.run_id).state
        self.assertEqual(after['runtime']['position']['actual_quantity'],before['runtime']['position']['actual_quantity'])
        self.assertEqual(len(after['broker']['payload']['submissions']),2)

    def test_prepared_run_without_exact_e6_paper_start_cannot_attach_or_mint_second_balance(self):
        from application.paper.engine import initial_runtime_state
        from brokers.paper import PaperBroker
        from registry import EvidenceGateError
        runtime=self.start(); accepted=self.process.recover(runtime.run_id)
        self.process.create_run('unaccepted-prepared-run',accepted.binding,
            dict(broker=PaperBroker().export_state(),runtime=initial_runtime_state(self.service,self.registry.get_strategy(self.identity))),
            now=self.clock[0])
        with self.assertRaises(EvidenceGateError): self.service.runtime('unaccepted-prepared-run')
        self.assertEqual(self.process.recover('unaccepted-prepared-run').revision,0)
        self.assertEqual(runtime.on_market_event(self.event(0,bars=True)).status,'ACKNOWLEDGED')

    def test_backward_wall_clock_denies_observation_without_poisoning_recovery(self):
        from storage.runtime_models import RuntimeValidationError
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True)); runtime.on_market_event(self.event(1))
        before=self.process.recover(runtime.run_id)
        self.clock[0]=self.initial_now
        with self.assertRaises(RuntimeValidationError): runtime.on_deadline(self.clock[0])
        after=self.process.recover(runtime.run_id)
        self.assertEqual(after.revision,before.revision); self.assertEqual(after.pending_operations,())
        self.assertEqual(runtime.on_market_event(self.event(2)).status,'HOLD')

    def test_actual_forward_quantitative_failure_cannot_mark_ready(self):
        from application.paper.assessment import assess_forward
        from registry import EvidenceGateError
        small=policy_fixture(); small.update(generation=2,min_elapsed_seconds=2,min_closed_trades=1,required_healthy_seconds=1)
        self.boundary.select_paper_policy('fixture-paper-loss-policy',small)
        self.service=self.make_service(simulation_fixture(),promotion=small,paper_policy_ref='fixture-paper-loss-policy')
        self.boundary._resolve=self.service.resolve_owner_evidence
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True)); runtime.on_market_event(self.event(1))
        runtime.on_market_event(self.event(2,'59989')); runtime.on_market_event(self.event(3,'59989'))
        body=assess_forward(runtime,self.service.promotion).as_dict()
        self.assertEqual(body['status'],'FAIL'); self.assertIn('MIN_NET_PNL_NOT_MET',body['reason_codes'])
        with self.assertRaises(EvidenceGateError):
            self.service.mark_ready(runtime.run_id,expected_revision=self.registry.get_strategy(self.identity).registry_revision,command_id='failed-ready')
        self.assertEqual(self.registry.get_strategy(self.identity).current_lifecycle_state,'PAPER')

    def test_immediate_pause_after_ack_defers_distinct_cancellation_observation(self):
        runtime=self.start(); runtime.on_market_event(self.event(0,bars=True))
        outcome=self.service.stop_new_entries(runtime.run_id,'pause-at-ack')
        self.assertIn('ENTRY_CANCELLATION_OBSERVATION_PENDING',outcome.reason_codes)
        state=self.process.recover(runtime.run_id).state
        self.assertFalse(state['runtime']['paper_entries_allowed'])
        self.assertEqual(state['broker']['payload']['submissions'][0]['order']['result']['order_status'],'OPEN')
        self.event(1); runtime.on_deadline(self.clock[0])
        state=self.process.recover(runtime.run_id).state
        self.assertEqual(state['broker']['payload']['submissions'][0]['order']['result']['order_status'],'CANCELED')
        self.assertEqual(state['broker']['payload']['submissions'][0]['order']['fills'],[])
        self.assertEqual(self.process.recover(runtime.run_id).pending_operations,())


if __name__ == '__main__': unittest.main()
