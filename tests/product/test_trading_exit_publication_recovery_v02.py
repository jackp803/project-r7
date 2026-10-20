"""ONE real EXIT commit-prefix/successor recovery case."""
import json
import unittest
from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import patch

from storage.product_dispatch import ProductDispatchError
from storage.runtime import PaperRuntimeJournal
from tests.product import h01_original_exit_fixture as original_fixtures
from tests.product import h01_exit_failure_fixtures as helpers


class TradingExitPublicationRecoveryV02Tests(unittest.TestCase):
    def test_actual_exit_action_commit_before_error_replays_exactly_on_genuine_successor_without_http(self):
        with original_fixtures.H01OriginalExitFixture(self) as c:
            f=c.f;entry_id=c.entry_decision.decision_id
            anchor,arguments=helpers.at_original_deadline(c)
            before_calls=tuple(c.provider.calls);commits=[]
            original_descriptor=PaperRuntimeJournal.persist_position_action
            def commit_actual_descriptor_then_fail(journal,payload):
                # PaperRuntimeJournal uses __slots__: patch class descriptor with
                # autospec. Invoke the REAL canonical owner writer first.
                stored=original_descriptor(journal,payload)
                if journal is f.canonical and payload.get('action')=='EXIT':
                    commits.append(stored)
                    raise OSError('FIXTURE_EXIT_ACTION_COMMITTED_BEFORE_RECEIPT')
                return stored
            with patch.object(PaperRuntimeJournal,'persist_position_action',autospec=True,
                              side_effect=commit_actual_descriptor_then_fail):
                with self.assertRaisesRegex(OSError,'FIXTURE_EXIT_ACTION_COMMITTED_BEFORE_RECEIPT'):
                    c.runner.evaluate_original_exit(f.bundle.boundary,**arguments)
            self.assertEqual(1,len(commits))
            decision=f.dispatch.exit_decision(c.service.run_id,entry_id)
            action=decision.evidence['position_action'];operation_id=decision.evidence['operation_id']
            self.assertEqual(['E5_MAX_HOLD_REACHED'],action['reason_codes'])
            self.assertEqual([dict(kind='POSITION_ACTION',payload=action)],decision.effects)
            self.assertEqual(action,commits[0].payload)
            self.assertEqual((decision,),f.dispatch.pending_exit_publications(c.service.run_id))
            before_rows=helpers.exit_rows(f.dispatch,c.service.run_id,entry_id)
            self.assertEqual((),before_rows['product_exit_publications'])
            self.assertEqual(1,len(before_rows['product_exit_decisions']))
            actual_action=helpers.canonical_action(f.canonical,action['position_action_id'])
            self.assertEqual(action,json.loads(actual_action['payload_json']))
            self.assertIsNone(f.dispatch.operation(c.service.run_id,operation_id),'No E4 prepare/claim/POST before action publication completes')
            self.assertEqual(before_calls,tuple(c.provider.calls))
            self.assertEqual('OPEN_PROTECTED',c.assert_binding().current_position_projection.payload['lifecycle_state'])
            old_lease=c.service.lease;release=f.authority.release[0]

            # Deliberately expire original action and all technical reads before
            # history-only drain. No old issued read object is given to successor.
            c.clock[0]+=timedelta(seconds=60)
            self.assertGreater(c.clock[0],arguments['action_expires_at'])
            with ExitStack() as stack:
                successor=helpers.successor(c,stack)
                self.assertEqual(2,successor.lease.generation)
                self.assertNotEqual(old_lease.instance_id,successor.lease.instance_id)
                self.assertEqual(release,f.authority.release[0])
                self.assertEqual(1,f.authority.release[0].runtime_generation)
                self.assertIsNot(successor.admission,c.service.admission)
                self.assertIsNot(successor.translator,c.service.translator)
                self.assertIsNot(successor.translator.capabilities,c.service.translator.capabilities)
                self.assertIsNot(successor.provider,c.provider)
                self.assertIsNot(successor.dispatch,f.dispatch)
                self.assertIsNot(successor.canonical,f.canonical)
                self.assertEqual({},successor._position_reads)
                self.assertEqual({},successor._close_preparations)
                self.assertEqual([],successor.provider.calls)
                successor.recover_publications()
                self.assertEqual((),successor.dispatch.pending_exit_publications(c.service.run_id))
                self.assertEqual(decision,successor.dispatch.exit_decision(c.service.run_id,entry_id))
                self.assertEqual(anchor,successor.dispatch.exit_anchor(c.service.run_id,entry_id))
                self.assertEqual(actual_action,helpers.canonical_action(successor.canonical,action['position_action_id']))
                after_rows=helpers.exit_rows(successor.dispatch,c.service.run_id,entry_id)
                self.assertEqual(before_rows['product_exit_anchors'],after_rows['product_exit_anchors'])
                self.assertEqual(before_rows['product_exit_decisions'],after_rows['product_exit_decisions'])
                self.assertEqual(1,len(after_rows['product_exit_publications']))
                receipt=after_rows['product_exit_publications'][0]
                self.assertEqual(2,receipt['generation'])
                self.assertEqual(decision.decision_id,receipt['decision_id'])
                self.assertEqual(decision.evidence_hash,receipt['evidence_hash'])
                self.assertEqual(decision.effects_hash,receipt['effects_hash'])
                self.assertIsNone(successor.dispatch.operation(c.service.run_id,operation_id))
                self.assertEqual([],successor.provider.calls)
                self.assertEqual(before_calls,tuple(c.provider.calls))

                successor.recover_publications()
                self.assertEqual(after_rows,helpers.exit_rows(successor.dispatch,c.service.run_id,entry_id))
                self.assertEqual(actual_action,helpers.canonical_action(successor.canonical,action['position_action_id']))
                self.assertEqual([],successor.provider.calls)
                self.assertFalse(successor.provider._responses)
                with self.assertRaises(ProductDispatchError) as caught:
                    f.dispatch.require_process(old_lease,now=c.clock[0])
                self.assertEqual('DISPATCH_CURRENT_PROCESS_GENERATION_REQUIRED',caught.exception.code)
                with self.assertRaises(ProductDispatchError) as caught:
                    c.service.recover_publications()
                self.assertEqual('DISPATCH_CURRENT_PROCESS_GENERATION_REQUIRED',caught.exception.code)
                self.assertEqual(before_calls,tuple(c.provider.calls))
                self.assertEqual(2,len([row for row in c.provider.calls if row['method']=='POST']))
