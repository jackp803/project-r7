"""Lost ACK obligation outranks expired entry inputs."""
from datetime import timedelta
import unittest

from tests.product import h01_entry_recovery_fixture as recovery_fixtures
from application.trading.orchestrator import TradingOrchestrator


class H01EntryLostAckTests(unittest.TestCase):
    def test_lost_ack_expired_plan_and_proof_reconcile_original_claim_once_without_new_post(self):
        with recovery_fixtures.H01RecoveryFixture() as h:
            f = h.fixture
            service, provider = h.install_initial_script(['LOST_ACK',f.order_response,f.fill_response])
            first = TradingOrchestrator(service).evaluate_entry(f.bundle, **f.arguments)
            self.assertEqual('RECONCILIATION_REQUIRED',first.dispatch_outcome.status)
            self.assertEqual(['POST'],[row['method'] for row in provider.calls])
            saved = f.dispatch.entry_decision(service.run_id,f.authority.identity,f.bundle.boundary)
            original = f.dispatch.operation(service.run_id,first.operation_id)
            self.assertEqual('READBACK_REQUIRED',original.recovery_disposition)
            f.authority.clock[0] += timedelta(seconds=60)
            from datetime import datetime
            expiry = datetime.fromisoformat(f.plan['expires_at'].replace('Z','+00:00'))
            self.assertGreater(f.authority.clock[0],expiry)
            self.assertGreater(f.authority.clock[0],f.proof.expires_at)
            # Genuinely new orchestration cache; same original actual service.
            second = TradingOrchestrator(service).evaluate_entry(f.bundle, **f.arguments)
            self.assertEqual(first.decision_id,second.decision_id)
            self.assertEqual(first.operation_id,second.operation_id)
            self.assertEqual(('ORIGINAL_CLAIM_READBACK',),second.reason_codes)
            self.assertEqual('ORDER_OBSERVED',second.dispatch_outcome.status)
            self.assertEqual(['POST','GET','GET'],[row['method'] for row in provider.calls])
            self.assertEqual(['/api/v5/trade/order','/api/v5/trade/fills'],
                             [row['path'] for row in provider.calls[1:]])
            self.assertEqual(original.request_json,f.dispatch.operation(service.run_id,first.operation_id).request_json)
            self.assertEqual(saved,f.dispatch.entry_decision(service.run_id,f.authority.identity,f.bundle.boundary))
            recovered = f.canonical.recover(trade_plan_id=f.plan['trade_plan_id'])
            self.assertEqual(f.risk,recovered.risk_decision.payload)
            self.assertEqual(f.plan,recovered.approved_trade_plan.payload)
            self.assertEqual(1,len(recovered.order_requests)); self.assertEqual((),recovered.fills)
