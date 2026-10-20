"""Bounded genuine cleanup regressions: TradingCleanupRecoveryV02Tests."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_protected_close_v02 as fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures

from tests.product.trading_stop_cleanup_fixtures import StopCleanupFixture


class TradingCleanupRecoveryV02Tests(StopCleanupFixture,unittest.TestCase):
    def test_lost_cancel_ack_keeps_claim_then_native_terminal_is_reconciled_without_another_cancel(self):
        self.flat();prepared=self.prepare(self.reads());self.flow.append('LOST_ACK')
        outcome=self.execute(prepared);self.assertEqual(outcome.status,'CLEANUP_READBACK_REQUIRED')
        self.assertEqual(self.execute(prepared),outcome);self.assertEqual(len(self.cancel_calls()),1)
        self.fixture.clock[0]+=timedelta(seconds=1)
        self.flow.append(dict(code='0',data=[self.algo(state='canceled')]))
        result=self.service.reconcile(self.flow.stop.canonical_request.order_request_id,expected_revision=self.fixture.revision)
        self.assertEqual(result.status,'ALGO_OBSERVED')
        recovered=self.flow.recover();stop=next(r.payload for r in recovered.current_order_results
            if r.payload['order_request_id']==self.flow.stop.canonical_request.order_request_id)
        self.assertEqual(stop['order_status'],'CANCELED');self.assertEqual(len(self.cancel_calls()),1)
        self.assertIsNone(recovered.trade_result);self.assertEqual(recovered.current_position_projection.payload['lifecycle_state'],'EXIT_REQUESTED')

    def test_successor_process_generation_two_reads_original_stop_without_resending_cancel(self):
        self.flat();prepared=self.prepare(self.reads());self.flow.append("LOST_ACK");self.execute(prepared)
        self.assertEqual(len(self.cancel_calls()),1)
        # self is TradingStopCleanupV02Tests after real flat + cleanup LOST_ACK.
        from dataclasses import replace
        from datetime import timedelta
        from tests.integration.test_runtime_preflight import RuntimePreflightV01Tests
        from registry.operational_authority import stamp
        from application.trading.admission import RuntimeAdmission
        from application.trading.service import TradingService
        from application.trading.provider import FakeProductProvider
        from brokers.okx_product_capability import OKXProductCapabilityOwner
        from brokers.okx_product import OKXProductTranslator
        from storage.product_dispatch import open_product_dispatch_journal
        from storage.runtime import open_paper_runtime_journal

        self.fixture.clock[0] += timedelta(seconds=1)
        successor_started_at = self.fixture.clock[0]
        successor_instance = 'process-fixture-cleanup-successor-002'

        def successor_preflight():
            base = RuntimePreflightV01Tests(); base.setUp()
            release = self.fixture.release[0]
            base.revision = release.executable_revision
            base.config_hash = release.config_hash
            base.capability_hash = release.capability_hash
            base.authorization_capability_hash = release.capability_hash
            value = base._input(role='PAPER_RUNTIME')
            now = self.fixture.clock[0]
            runtime_generation = 'runtime-generation:' + str(release.runtime_generation)
            config_generation = 'config-generation:' + str(release.config_generation)
            authorization = dict(value.authorization_evidence,
                authorization_class='PERSISTENT_LIVE_RUNTIME', authorized_runtime_role='LIVE_RUNTIME')
            value = replace(value,
                runtime_preflight_profile_version='product-runtime-preflight-v0.2',
                runtime_role='LIVE_RUNTIME', requested_operational_mode='LIVE',
                evaluated_at=stamp(now), process_instance_id=successor_instance,
                process_start_generation_id=runtime_generation,
                process_started_at=stamp(successor_started_at),
                runtime_config_generation_id=config_generation,
                heartbeat_evidence=dict(value.heartbeat_evidence,
                    heartbeat_process_instance_id=successor_instance,
                    heartbeat_process_start_generation_id=runtime_generation,
                    heartbeat_observed_at=stamp(now), heartbeat_received_at=stamp(now)),
                reconciliation_evidence=dict(value.reconciliation_evidence,
                    reconciliation_observed_at=stamp(now)),
                external_consumer_evidence=dict(value.external_consumer_evidence,
                    compatibility_observed_at=stamp(now)),
                authorization_evidence=authorization)
            authority = base._authority(value)
            authority = replace(authority,
                runtime_config_authority=dict(authority.runtime_config_authority,
                    runtime_config_generation_id=config_generation))
            return value, authority

        new_admission = RuntimeAdmission(namespace='FIXTURE', registry_factory=self.fixture.factory,
            current_preflight=successor_preflight, clock=lambda: self.fixture.clock[0],
            maximum_observation_age_seconds=5)
        new_capabilities = OKXProductCapabilityOwner()
        new_translator = OKXProductTranslator(new_capabilities)
        new_dispatch = open_product_dispatch_journal(self.fixture.root/'dispatch.sqlite')
        new_canonical = open_paper_runtime_journal(self.fixture.root/'canonical.sqlite')
        self.addCleanup(new_dispatch.close); self.addCleanup(new_canonical.close)
        # Only actual canceled target response; this source cannot submit an effect.
        new_provider = FakeProductProvider([dict(code='0',data=[self.algo(state='canceled')])])
        successor = TradingService(admission=new_admission, translator=new_translator,
            dispatch=new_dispatch, canonical=new_canonical, provider=new_provider,
            identity=self.fixture.identity, run_id=self.service.run_id,
            clock=lambda: self.fixture.clock[0])
        prior_claim = self.service.dispatch.stop_cleanup_claim(self.service.run_id,
            self.flow.stop.canonical_request.order_request_id)
        self.assertIsNotNone(prior_claim)
        old_lease = self.service.lease
        lease = successor.bind_process(expected_revision=self.fixture.revision, expected_generation=1)
        self.assertEqual(2, lease.generation)
        self.assertEqual(successor_instance, lease.instance_id)
        self.assertNotEqual(old_lease.instance_id, lease.instance_id)
        # No issuing old read/proof/preparation object to successor, no replayed cancel.
        successor.recover_publications()
        result = successor.reconcile(self.flow.stop.canonical_request.order_request_id,
                                     expected_revision=self.fixture.revision)
        self.assertEqual('ALGO_OBSERVED', result.status)
        self.assertTrue(new_provider.calls)
        self.assertTrue(all(row['method']=='GET' for row in new_provider.calls))
        self.assertEqual(['/api/v5/trade/order-algo'], [row['path'] for row in new_provider.calls])
        self.assertEqual(prior_claim, new_dispatch.stop_cleanup_claim(successor.run_id,
            self.flow.stop.canonical_request.order_request_id))
        recovered = new_canonical.recover(trade_plan_id=self.flow.recover().trade_plan_id)
        stop_result = next(row.payload for row in recovered.current_order_results
            if row.payload['order_request_id']==self.flow.stop.canonical_request.order_request_id)
        self.assertEqual('CANCELED', stop_result['order_status'])
        self.assertIsNone(recovered.trade_result)
        self.assertEqual('EXIT_REQUESTED', recovered.current_position_projection.payload['lifecycle_state'])
        # Actual result arrival can require E5 execution reinterpretation; do not claim
        # restart_authoritative merely from successful targeted cancel readback.
        with self.assertRaises(ValueError):
            self.service.dispatch.require_process(old_lease,now=self.fixture.clock[0])
        self.assertEqual(len(self.cancel_calls()),1)
