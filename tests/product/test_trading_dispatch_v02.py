"""Actual E6/E7/E5/E4 dispatch mechanics, scripted provider only; no real I/O."""
import importlib
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import tests.product.test_live_admission_v02 as admission_fixtures
import tests.brokers.test_okx_demo_adapter as metadata_fixtures
import tests.risk.test_approved_plan_consumer_v02 as risk_fixtures
from application.trading.admission import RuntimeAdmission, RuntimeAdmissionError
from brokers.okx_demo import OKXAccountConfigSnapshot, OKXPrerequisiteSnapshot
from brokers.okx_product_capability import OKXProductCapabilityOwner
from brokers.okx_product import OKXProductTranslator
from storage.product_dispatch import open_product_dispatch_journal
from storage.runtime import open_paper_runtime_journal


class TradingDispatchV02Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = admission_fixtures.LiveAdmissionV02Tests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.admission = RuntimeAdmission(namespace='FIXTURE', registry_factory=self.fixture.factory,
            current_preflight=self.fixture.preflight, clock=lambda: self.fixture.clock[0], maximum_observation_age_seconds=5)
        self.dispatch = open_product_dispatch_journal(self.fixture.root / 'dispatch.sqlite')
        self.canonical = open_paper_runtime_journal(self.fixture.root / 'canonical.sqlite')
        self.addCleanup(self.dispatch.close); self.addCleanup(self.canonical.close)
        self.capabilities = OKXProductCapabilityOwner(); self.translator = OKXProductTranslator(self.capabilities)
        self.risk, self.plan, _ = risk_fixtures.approved(self.fixture.identity, self.fixture.clock[0])
        self.canonical.persist_risk_decision(self.risk); self.canonical.persist_approved_trade_plan(self.plan)
        self.prepared = self.entry()

    def entry(self, plan=None):
        now = self.fixture.clock[0]
        account = OKXAccountConfigSnapshot('2', 'net_mode', '123', '123')
        metadata = replace(metadata_fixtures._metadata(now), ct_val=Decimal('0.0001'))
        proof = self.capabilities.issue('ENTRY', account, metadata, observed_at=now, now=now)
        prerequisites=OKXPrerequisiteSnapshot(account, (), ())
        prerequisites_proof=self.capabilities.observe_entry_prerequisites(prerequisites,observed_at=now,now=now)
        return self.translator.prepare_entry(plan=self.plan if plan is None else plan, metadata=metadata,
                 prerequisites=prerequisites, prerequisites_proof=prerequisites_proof, proof=proof, now=now)

    def api(self):
        try: return importlib.import_module('application.trading.service')
        except ModuleNotFoundError: self.fail('Missing actual trading effect composition')

    def service(self, script):
        api = self.api()
        provider = api.FakeProductProvider(script)
        service = api.TradingService(admission=self.admission, translator=self.translator,
            dispatch=self.dispatch, canonical=self.canonical, provider=provider,
            identity=self.fixture.identity, run_id='fixture-run', clock=lambda: self.fixture.clock[0])
        service.bind_process(expected_revision=self.fixture.revision, expected_generation=0)
        return service, provider

    def ack(self):
        return dict(code='0', data=[dict(ordId='1234', clOrdId=self.prepared.materialization.provider_cl_ord_id, sCode='0')])

    def order(self, **changes):
        row = dict(self.prepared.materialization.body)
        row.update(instType='SWAP', ordId='1234', state='live', accFillSz='0', avgPx='0', reduceOnly=False)
        row.update(changes)
        return dict(code='0', data=[row])

    def fill_rows(self):
        return dict(code='0', data=[dict(instId='BTC-USDT-SWAP', clOrdId=self.prepared.materialization.provider_cl_ord_id,
            ordId='1234', tradeId='1', side='buy', posSide='net', fillSz='4', fillPx='60000',
            fillTime=str(int(self.fixture.clock[0].timestamp() * 1000)), fee='-0.012', feeCcy='USDT')])

    def stop(self):
        from brokers.paper_state import decode_fact
        from execution.models import OrderRequest, OrderResult, Fill, PositionExposureSnapshot
        from position.entry_observation import build_product_entry_projection
        from position import build_position_lifecycle_execution_evidence_binding, CurrentProtectionRegistryAuthority
        from position.protection import build_protect_position_action
        from position.lifecycle_projection import _broker_fact_payload
        from execution.protection_trigger import prepare_trigger_validated_protection_order
        from execution.protection_registry_evidence_boundary import build_protection_registry_multiplicity_evidence
        from position.protection_registry_policy import canonical_protection_registry_hash
        from position.protection_trigger_validity import build_protection_trigger_validity_evidence
        import tests.execution.test_protection_registry_evidence as registry_fixtures
        service, _ = self.service([self.ack(), self.order(state='partially_filled', accFillSz='4', avgPx='60000'), self.fill_rows()])
        service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.fixture.clock[0] += timedelta(seconds=2)
        service.reconcile(self.prepared.canonical_request.order_request_id, expected_revision=self.fixture.revision)
        now=self.fixture.clock[0]
        recovered=self.canonical.recover(trade_plan_id=self.plan['trade_plan_id'])
        requests=tuple(decode_fact(OrderRequest, item.payload) for item in recovered.order_requests)
        results=tuple(decode_fact(OrderResult, item.payload) for item in recovered.order_result_observations)
        fills=tuple(decode_fact(Fill, item.payload) for item in recovered.fills)
        current=decode_fact(OrderResult, recovered.current_order_results[0].payload)
        projections=build_product_entry_projection(self.plan, self.prepared.canonical_request, current, fills,
            PositionExposureSnapshot('BTC_USDT_PERP', Decimal('0.0004')), observed_at=now).projections
        position=projections[-1].lifecycle_projection
        self.canonical.persist_raw_position_observation(dict(_broker_fact_payload(position), lifecycle_state=position['lifecycle_state']))
        for projection in projections:
            self.canonical.persist_position_projection(projection.lifecycle_projection)
            binding=build_position_lifecycle_execution_evidence_binding(projection.lifecycle_projection,
                order_requests=requests, order_results=results, fills=fills)
            self.canonical.persist_lifecycle_execution_binding(binding)
        action=build_protect_position_action(position, self.plan, created_at=now, expires_at=now+timedelta(seconds=30))
        self.canonical.persist_position_action(action)
        stamp=now.isoformat().replace('+00:00','Z')
        market=dict(schema_version='contracts-v0.1', symbol='BTC_USDT_PERP', source='FIXTURE_MARKET',
            observed_at=stamp, received_at=stamp, health_status='HEALTHY', last_price='60000', freshness_ms=0)
        trigger=build_protection_trigger_validity_evidence(position, action, self.plan, market,
            market_freshness_classification='FRESH', evaluated_at=now)
        request=prepare_trigger_validated_protection_order(action, self.plan, position, trigger, market,
            market_freshness_classification='FRESH', now=now)
        fixture=registry_fixtures.ProtectionRegistryMultiplicityEvidenceTests(methodName='runTest'); fixture.setUp()
        fixture.provider_observed_at=now; fixture.provider_received_at=now; fixture.evaluated_at=now
        lineage=fixture.intended_lineage(position, position_action_id=action['position_action_id'],
            position_action_hash=canonical_protection_registry_hash(action), approved_trade_plan_hash=canonical_protection_registry_hash(self.plan),
            protection_order_request_hash=canonical_protection_registry_hash(request), protection_order_request_ref=request.order_request_id,
            trigger_validity_ref=trigger['protection_trigger_validity_id'], lifecycle_projection_ref=position['lifecycle_projection_id'],
            lifecycle_execution_binding_ref=binding['lifecycle_execution_binding_id'])
        value=fixture.input_for(position=position, lineage=lineage, observed_set=fixture.observed_set([]),
            lifecycle_projection_ref=position['lifecycle_projection_id'], lifecycle_execution_binding_ref=binding['lifecycle_execution_binding_id'])
        evidence=build_protection_registry_multiplicity_evidence(value)
        authority=CurrentProtectionRegistryAuthority(evidence['position_ref'], evidence['position_hash'], position, position, binding,
            evidence['provider_identity_ref'], evidence['provider_instrument_ref'], evidence['provider_observation_generation_id'],
            evidence['provider_observed_at'], evidence['provider_received_at'], evidence['observed_active_protection_set_hash'])
        metadata=replace(metadata_fixtures._metadata(now), ct_val=Decimal('0.0001'))
        proof=self.capabilities.issue('PROTECTION_STOP', OKXAccountConfigSnapshot('2','net_mode','123','123'), metadata, observed_at=now, now=now)
        prepared=self.translator.prepare_protection(action=action, plan=self.plan, position=position, trigger_evidence=trigger,
            market=market, market_freshness_classification='FRESH', registry_evidence=evidence, registry_authority=authority,
            metadata=metadata, proof=proof, now=now)
        return service, prepared

    def test_initial_protection_uses_actual_partial_position_and_triggered_child_keeps_native_lineage(self):
        from brokers.paper_state import encode_fact
        from execution.models import OrderResult, ExecutionHealthStatus, OrderStatus
        service, prepared=self.stop()
        self.assertEqual('4', prepared.materialization.body['sz'])
        native=prepared.materialization.provider_cl_ord_id
        algo=dict(prepared.materialization.body)
        algo.update(instType='SWAP', algoId='2345', state='effective', ordIdList=['3456'], ordId='3456',
                    actualSz='1', actualPx='59400', failCode='')
        child={key: algo[key] for key in ('instId','tdMode','posSide','side','sz','reduceOnly')}
        child.update(instType='SWAP', ordType='market', clOrdId='CHILD123', ordId='3456',
                     state='partially_filled', accFillSz='1', avgPx='59400')
        rows=dict(code='0', data=[dict(instId='BTC-USDT-SWAP', clOrdId='CHILD123', ordId='3456', tradeId='2',
            side='sell', posSide='net', fillSz='1', fillPx='59400', fee='-0.01', feeCcy='USDT',
            fillTime=str(int(self.fixture.clock[0].timestamp()*1000)))])
        provider=self.api().FakeProductProvider([dict(code='0',data=[dict(algoId='2345',algoClOrdId=native,sCode='0')]),
            dict(code='0',data=[algo]),dict(code='0',data=[child]),rows])
        service.provider=provider
        service.execute(prepared, expected_revision=self.fixture.revision)
        self.fixture.clock[0] += timedelta(seconds=2)
        result=service.reconcile(prepared.canonical_request.order_request_id, expected_revision=self.fixture.revision)
        self.assertEqual('ALGO_OBSERVED',result.status)
        self.assertEqual(['POST','GET','GET','GET'], [call['method'] for call in provider.calls])
        recovered=self.canonical.recover(trade_plan_id=self.plan['trade_plan_id'])
        stop_fills=[item.payload for item in recovered.fills if item.payload['order_role']=='PROTECTION_STOP']
        self.assertEqual(1,len(stop_fills)); self.assertEqual('3456',stop_fills[0]['broker_order_id'])
        self.assertEqual(prepared.canonical_request.position_action_id,stop_fills[0]['position_action_id'])
        self.assertNotEqual('CLOSED', recovered.current_position_projection.payload['lifecycle_state'])

    def test_actual_owners_commit_claim_before_one_post_and_publish_only_pending_ack(self):
        service, provider = self.service([self.ack()])
        outcome = service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.assertEqual('ACK_PENDING', outcome.status)
        self.assertEqual(['POST'], [call['method'] for call in provider.calls])
        operation = self.dispatch.operation('fixture-run', self.prepared.canonical_request.order_request_id)
        self.assertEqual('READBACK_REQUIRED', operation.recovery_disposition)
        recovered = self.canonical.recover(trade_plan_id=self.plan['trade_plan_id'])
        self.assertEqual('PENDING', recovered.current_order_results[0].payload['order_status'])
        self.assertEqual('0', recovered.current_order_results[0].payload['filled_quantity'])
        self.assertEqual((), recovered.fills)
        self.assertEqual((), self.dispatch.pending_publications('fixture-run'))

    def test_duplicate_execute_reconciles_same_committed_claim_without_another_post(self):
        service, provider=self.service([self.ack(), self.order(), dict(code='0',data=[])])
        service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.fixture.clock[0] += timedelta(milliseconds=100)
        outcome=service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.assertEqual('ORDER_OBSERVED',outcome.status)
        self.assertEqual(['POST','GET','GET'], [call['method'] for call in provider.calls])

    def test_an_unresolved_entry_claim_blocks_another_plan_despite_a_new_empty_prerequisite_snapshot(self):
        service, provider=self.service([self.ack(),self.ack()])
        service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.fixture.clock[0] += timedelta(milliseconds=100)
        risk, plan, _=risk_fixtures.approved(self.fixture.identity,self.fixture.clock[0])
        self.canonical.persist_risk_decision(risk);self.canonical.persist_approved_trade_plan(plan)
        newer=self.entry(plan)
        self.assertNotEqual(self.prepared.canonical_request.order_request_id,newer.canonical_request.order_request_id)
        with self.assertRaises(ValueError): service.execute(newer,expected_revision=self.fixture.revision)
        self.assertEqual(['POST'],[call['method'] for call in provider.calls])
        self.assertIsNone(self.dispatch.operation('fixture-run',newer.canonical_request.order_request_id))

    def test_fixture_cannot_compose_real_driver_and_constructor_reads_no_vault(self):
        from application.trading.provider import ProductionProductProvider
        from brokers.okx_production_transport import OKXProductionTransportConfig, LocalSecureCredentialProvider
        reads=[]
        provider=ProductionProductProvider(config=OKXProductionTransportConfig('https://www.okx.com','https://www.okx.com'),
            vault=LocalSecureCredentialProvider(read_secret=lambda *args: reads.append(args)),
            credential_handle='fixture', account_ref='fixture-account', account_hash='sha256:'+'1'*64, provider_ref='fixture-paper')
        with self.assertRaises(ValueError):
            self.api().TradingService(admission=self.admission, translator=self.translator, dispatch=self.dispatch,
                canonical=self.canonical, provider=provider, identity=self.fixture.identity, run_id='fixture-run', clock=lambda:self.fixture.clock[0])
        self.assertEqual([],reads)

    def test_explicit_rejection_with_zero_fills_can_clear_after_fresh_current_prerequisites(self):
        reject=self.ack();reject['data'][0].update(sCode='51000',ordId='',sMsg='private fake provider message')
        service, provider=self.service([reject])
        self.assertEqual('ACK_REJECTED',service.execute(self.prepared,expected_revision=self.fixture.revision).status)
        self.fixture.clock[0] += timedelta(milliseconds=100)
        risk,plan,_=risk_fixtures.approved(self.fixture.identity,self.fixture.clock[0])
        self.canonical.persist_risk_decision(risk);self.canonical.persist_approved_trade_plan(plan)
        newer=self.entry(plan)
        next_provider=self.api().FakeProductProvider([dict(code='0',data=[dict(ordId='9999',sCode='0',
            clOrdId=newer.materialization.provider_cl_ord_id)])])
        service.provider=next_provider
        self.assertEqual('ACK_PENDING',service.execute(newer,expected_revision=self.fixture.revision).status)
        self.assertEqual(['POST'],[call['method'] for call in provider.calls])
        self.assertEqual(['POST'],[call['method'] for call in next_provider.calls])

    def test_lost_ack_restart_only_reads_back_even_when_lookup_is_empty(self):
        service, provider = self.service(['LOST_ACK'])
        outcome = service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.assertEqual('RECONCILIATION_REQUIRED', outcome.status)
        self.fixture.clock[0] += timedelta(seconds=2)
        original_preflight = self.fixture.preflight
        def restarted():
            value, authority = original_preflight()
            return replace(value, process_instance_id='process-fixture-002',
                           heartbeat_evidence=dict(value.heartbeat_evidence, heartbeat_process_instance_id='process-fixture-002')), authority
        self.admission.current_preflight = restarted
        api = self.api(); next_provider = api.FakeProductProvider([dict(code='0', data=[])])
        resumed = api.TradingService(admission=self.admission, translator=OKXProductTranslator(OKXProductCapabilityOwner()),
            dispatch=self.dispatch, canonical=self.canonical, provider=next_provider,
            identity=self.fixture.identity, run_id='fixture-run', clock=lambda: self.fixture.clock[0])
        resumed.bind_process(expected_revision=self.fixture.revision, expected_generation=1)
        result = resumed.reconcile(self.prepared.canonical_request.order_request_id, expected_revision=self.fixture.revision)
        self.assertEqual('RECONCILIATION_REQUIRED', result.status)
        self.assertEqual(['GET'], [call['method'] for call in next_provider.calls])
        self.assertEqual(['POST'], [call['method'] for call in provider.calls])
        self.assertEqual((), self.canonical.recover(trade_plan_id=self.plan['trade_plan_id']).fills)

    def test_current_consent_is_rechecked_after_durable_claim_before_provider_effect(self):
        service, provider = self.service([self.ack()])
        claim = self.dispatch.claim_dispatch
        def revoke(*args, **kwargs):
            result = claim(*args, **kwargs)
            self.fixture.e6.revoke_approval(self.fixture.identity,
                authenticated_human=self.fixture.auth.authenticate('FIXTURE_AUTH_PROOF'), reason='fixture', command_id='during-claim')
            return result
        with patch.object(self.dispatch, 'claim_dispatch', side_effect=revoke), self.assertRaises(ValueError):
            service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.assertEqual([], provider.calls)
        self.assertEqual('DISPATCHING', self.dispatch.operation('fixture-run', self.prepared.canonical_request.order_request_id).status)

    def test_permit_expiring_inside_final_provider_guard_cannot_reach_post(self):
        service,provider=self.service([self.ack()]);original=self.dispatch.iter_claimed_entries_for_account
        reads=[]
        def slow_last_read(*args,**kwargs):
            result=original(*args,**kwargs);reads.append(True)
            yield from result
            if len(reads)==3:self.fixture.clock[0]+=timedelta(seconds=2)
        with patch.object(self.dispatch,'iter_claimed_entries_for_account',side_effect=slow_last_read),self.assertRaises(RuntimeAdmissionError):
            service.execute(self.prepared,expected_revision=self.fixture.revision)
        self.assertEqual(3,len(reads))
        self.assertEqual([],provider.calls)
        self.assertEqual('DISPATCHING',self.dispatch.operation('fixture-run',self.prepared.canonical_request.order_request_id).status)

    def test_same_plan_id_with_different_exact_e5_payload_cannot_dispatch(self):
        changed = dict(self.plan, quantity='0.002')
        prepared = self.entry(changed)
        service, provider = self.service([self.ack()])
        with self.assertRaises(ValueError): service.execute(prepared, expected_revision=self.fixture.revision)
        self.assertEqual([], provider.calls)
        self.assertIsNone(self.dispatch.operation('fixture-run', prepared.canonical_request.order_request_id))

    def test_publication_failure_replays_retained_facts_without_post_or_get(self):
        service, provider = self.service([self.ack()])
        with patch.object(type(self.canonical), 'persist_order_result', side_effect=OSError('fixture disk error')):
            with self.assertRaises(OSError): service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.assertEqual(1, len(self.dispatch.pending_publications('fixture-run')))
        service.recover_publications()
        self.assertEqual(['POST'], [call['method'] for call in provider.calls])
        self.assertEqual((), self.dispatch.pending_publications('fixture-run'))
        self.assertEqual(1, len(self.canonical.recover(trade_plan_id=self.plan['trade_plan_id']).current_order_results))

    def test_partial_order_and_complete_fills_are_published_without_flat_inference(self):
        service, provider = self.service([self.ack(), self.order(state='partially_filled', accFillSz='4', avgPx='60000'),
            dict(code='0', data=[dict(instId='BTC-USDT-SWAP', clOrdId=self.prepared.materialization.provider_cl_ord_id,
              ordId='1234', tradeId='1', side='buy', posSide='net', fillSz='4', fillPx='60000',
              fillTime=str(int(self.fixture.clock[0].timestamp() * 1000)), fee='-0.012', feeCcy='USDT')])])
        service.execute(self.prepared, expected_revision=self.fixture.revision)
        self.fixture.clock[0] += timedelta(seconds=2)
        result = service.reconcile(self.prepared.canonical_request.order_request_id, expected_revision=self.fixture.revision)
        self.assertEqual('ORDER_OBSERVED', result.status)
        recovered = self.canonical.recover(trade_plan_id=self.plan['trade_plan_id'])
        self.assertEqual('PARTIALLY_FILLED', recovered.current_order_results[0].payload['order_status'])
        self.assertEqual(1, len(recovered.fills))
        self.assertIsNone(recovered.current_position_projection)
        self.assertEqual(['POST', 'GET', 'GET'], [call['method'] for call in provider.calls])


if __name__ == '__main__': unittest.main()
