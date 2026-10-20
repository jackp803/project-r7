"""ONE actual PREPARED/no-claim cold-wrapper case."""
import unittest
from datetime import timedelta
from unittest.mock import patch

from application.trading.orchestrator import TradingOrchestrator
from tests.product import h01_original_exit_fixture as original_fixtures
from tests.product import h01_exit_failure_fixtures as helpers


class TradingExitPreparedRecoveryV02Tests(unittest.TestCase):
    def test_durable_prepared_close_without_original_local_preparation_cannot_be_adopted_after_expiry(self):
        with original_fixtures.H01OriginalExitFixture(self) as c:
            f=c.f;entry_id=c.entry_decision.decision_id
            anchor,arguments=helpers.at_original_deadline(c)
            before_calls=tuple(c.provider.calls);prepared_seen=[]
            def fail_before_actual_claim_commit(run_id,operation_id,*,lease,now):
                # Normal TradingCoordinator already committed actual prepare().
                # Failure occurs before claim commit, never after a hidden POST.
                operation=f.dispatch.operation(run_id,operation_id)
                self.assertEqual('POSITION_EXIT',operation.request['role'])
                self.assertEqual('PREPARED',operation.status)
                self.assertEqual('CURRENT_ADMISSION_REQUIRED',operation.recovery_disposition)
                self.assertEqual(c.service.lease,lease)
                prepared_seen.append(operation)
                raise OSError('FIXTURE_EXIT_CLAIM_BEFORE_COMMIT')
            with patch.object(f.dispatch,'claim_dispatch',side_effect=fail_before_actual_claim_commit):
                with self.assertRaisesRegex(OSError,'FIXTURE_EXIT_CLAIM_BEFORE_COMMIT'):
                    c.runner.evaluate_original_exit(f.bundle.boundary,**arguments)
            self.assertEqual(1,len(prepared_seen))
            operation=prepared_seen[0]
            decision=f.dispatch.exit_decision(c.service.run_id,entry_id)
            self.assertEqual(operation.operation_id,decision.evidence['operation_id'])
            self.assertEqual(['E5_MAX_HOLD_REACHED'],decision.evidence['position_action']['reason_codes'])
            saved_rows=helpers.exit_rows(f.dispatch,c.service.run_id,entry_id)
            self.assertEqual(1,len(saved_rows['product_exit_publications']))
            action_before=helpers.canonical_action(f.canonical,decision.evidence['position_action']['position_action_id'])
            self.assertIsNotNone(action_before)
            self.assertEqual(before_calls,tuple(c.provider.calls))
            self.assertEqual('OPEN_PROTECTED',c.assert_binding().current_position_projection.payload['lifecycle_state'])

            # New wrapper has no issuer-local preparation, but uses SAME actual
            # service/provider. It must not translate/adopt/resend PREPARED.
            cold=TradingOrchestrator(c.service)
            c.clock[0]+=timedelta(seconds=60)
            self.assertGreater(c.clock[0],arguments['action_expires_at'])
            result=cold.evaluate_original_exit(f.bundle.boundary,**arguments)
            self.assertEqual('BLOCKED',result.status)
            self.assertEqual(('ORIGINAL_LOCAL_PREPARATION_REQUIRED',),result.reason_codes)
            self.assertEqual(decision.decision_id,result.decision_id)
            self.assertEqual(operation.operation_id,result.operation_id)
            self.assertIsNone(result.dispatch_outcome)
            self.assertEqual(anchor.anchor,result.anchor)
            self.assertEqual(operation,f.dispatch.operation(c.service.run_id,operation.operation_id))
            self.assertEqual(decision,f.dispatch.exit_decision(c.service.run_id,entry_id))
            self.assertEqual(saved_rows,helpers.exit_rows(f.dispatch,c.service.run_id,entry_id))
            self.assertEqual(action_before,helpers.canonical_action(f.canonical,decision.evidence['position_action']['position_action_id']))
            self.assertEqual(before_calls,tuple(c.provider.calls))
            self.assertEqual(2,len([row for row in c.provider.calls if row['method']=='POST']))
            self.assertFalse(c.provider._responses)
