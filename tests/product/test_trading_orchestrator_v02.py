"""Actual joined FIXTURE entry regression; native/H01 acceptance stays separate."""
import unittest
from datetime import timedelta
from unittest.mock import patch

from application.trading.admission import RuntimeAdmissionError
from tests.product import h01_entry_fixture as fixtures


class TradingOrchestratorV02Tests(unittest.TestCase):
    def test_actual_registered_e2_e5_entry_is_durable_before_one_guarded_fake_submission(self):
        with fixtures.H01EntryFixture() as f:
            from application.trading.orchestrator import TradingOrchestrator
            runner = TradingOrchestrator(f.service)
            self.assertEqual(f.authority.identity.strategy_id, f.signal['strategy_id'])
            self.assertEqual(f.authority.identity.strategy_version, f.signal['strategy_version'])
            self.assertEqual(f.record.content_hash, f.strategy.content_hash)
            self.assertEqual('LONG', f.signal['direction'])
            self.assertEqual('APPROVE', f.risk['decision'])  # Returned by actual E5, not injected.
            self.assertEqual(f.now, f.bundle.boundary)
            self.assertEqual(f.now, f.bundle.information_cutoff)
            self.assertEqual(f.now, f.bundle.visible('1h')[-1].close_time)
            initial = f.canonical.recover(trade_plan_id=f.plan['trade_plan_id'])
            self.assertIsNone(initial.risk_decision)
            self.assertIsNone(initial.approved_trade_plan)
            self.assertEqual([], f.provider.calls)
            expected_effects = [dict(kind='RISK_DECISION', payload=f.risk),
                                dict(kind='APPROVED_TRADE_PLAN', payload=f.plan)]
            decision_snapshots = []
            claims = []
            original_claim = f.dispatch.claim_dispatch
            original_request = f.provider.request

            def require_durable_e2_e5_before_claim(*args, **kwargs):
                # Narrow read port returns the actual immutable E6-local
                # decision batch. Spy forwards to real writer; no result override.
                decision = f.dispatch.entry_decision(f.service.run_id, f.authority.identity, f.bundle.boundary)
                self.assertIsNotNone(decision)
                self.assertEqual(expected_effects, decision.effects)
                self.assertEqual(f.signal, decision.signal)
                self.assertEqual(f.intent, decision.trade_intent)
                self.assertEqual(f.exit_request.as_dict(), decision.exit_request)
                self.assertEqual(f.record.content_hash, decision.strategy_content_hash)
                self.assertEqual(f.bundle.boundary, decision.boundary)
                recovered = f.canonical.recover(trade_plan_id=f.plan['trade_plan_id'])
                self.assertEqual(f.risk, recovered.risk_decision.payload)
                self.assertEqual(f.plan, recovered.approved_trade_plan.payload)
                decision_snapshots.append(decision)
                claims.append(args[1])
                return original_claim(*args, **kwargs)

            def require_claim_before_actual_fake_effect(method, path, **kwargs):
                if method == 'POST':
                    claimed = f.dispatch.operation(f.service.run_id, f.request.order_request_id)
                    self.assertIsNotNone(claimed)
                    self.assertEqual('READBACK_REQUIRED', claimed.recovery_disposition)
                    self.assertEqual(f.request.order_request_id, claimed.request['canonical_request']['order_request_id'])
                    recovered = f.canonical.recover(trade_plan_id=f.plan['trade_plan_id'])
                    self.assertEqual(f.risk, recovered.risk_decision.payload)
                    self.assertEqual(f.plan, recovered.approved_trade_plan.payload)
                return original_request(method, path, **kwargs)

            with patch.object(f.dispatch, 'claim_dispatch', side_effect=require_durable_e2_e5_before_claim), \
                    patch.object(f.provider, 'request', side_effect=require_claim_before_actual_fake_effect):
                first = runner.evaluate_entry(f.bundle, **f.arguments)
                self.assertEqual(f.request.order_request_id, first.operation_id)
                self.assertEqual('ACK_PENDING', first.dispatch_outcome.status)
                before = f.canonical.recover(trade_plan_id=f.plan['trade_plan_id'])
                f.authority.clock[0] += timedelta(seconds=1)  # Distinct actual result observation clock.
                repeated = runner.evaluate_entry(f.bundle, **f.arguments)
                self.assertEqual(first.decision_id, repeated.decision_id)
                self.assertEqual(first.operation_id, repeated.operation_id)
                self.assertEqual('ORDER_OBSERVED', repeated.dispatch_outcome.status)

            self.assertEqual([f.request.order_request_id], claims)
            self.assertEqual(1, len(decision_snapshots))
            self.assertEqual(decision_snapshots[0],f.dispatch.entry_decision(f.service.run_id,f.authority.identity,f.bundle.boundary), 'Exact saved decision, not a refreshed clock/plan')
            self.assertEqual(1, len([row for row in f.provider.calls if row['method']=='POST']))
            self.assertEqual(['POST', 'GET', 'GET'], [row['method'] for row in f.provider.calls])
            after = f.canonical.recover(trade_plan_id=f.plan['trade_plan_id'])
            self.assertEqual(before.risk_decision, after.risk_decision)
            self.assertEqual(before.approved_trade_plan, after.approved_trade_plan)
            self.assertEqual(1, len(after.order_requests))
            self.assertEqual((), after.fills, 'ACK and live zero-fill readback cannot manufacture fill')
            self.assertIsNone(after.trade_result)

            # Persisted accepted decision/plan cannot renew original authority.
            f.authority.e6.revoke_approval(f.authority.identity,
                authenticated_human=f.authority.auth.authenticate('FIXTURE_AUTH_PROOF'),
                reason='h01-existing-authority-revoked', command_id='h01-revoke-after-entry')
            call_count = len(f.provider.calls)
            with self.assertRaises(RuntimeAdmissionError):
                f.admission.issue(f.authority.identity, expected_revision=f.authority.revision,
                    permission='NEW_EXPOSURE', execution='FAKE_PROVIDER_VERIFICATION')
            self.assertEqual(call_count, len(f.provider.calls))
            # Existing obligations retain management after consent revocation,
            # and after original plan/technical entry proof expire.
            f.authority.clock[0] += timedelta(seconds=60)
            management=f.admission.evaluate(f.authority.identity,expected_revision=f.authority.revision,permission='MANAGE_EXISTING',execution='FAKE_PROVIDER_VERIFICATION')
            self.assertTrue(management.allowed,management.reason_codes)
            f.provider._responses.extend([f.order_response,f.fill_response])
            continued=runner.evaluate_entry(f.bundle,**f.arguments)
            self.assertEqual(first.decision_id,continued.decision_id)
            self.assertEqual(first.operation_id,continued.operation_id)
            self.assertEqual('ORDER_OBSERVED',continued.dispatch_outcome.status)
            self.assertEqual(call_count+2,len(f.provider.calls))
            self.assertEqual(1,len([row for row in f.provider.calls if row['method']=='POST']))
            self.assertEqual(decision_snapshots[0],
                f.dispatch.entry_decision(f.service.run_id, f.authority.identity, f.bundle.boundary))
