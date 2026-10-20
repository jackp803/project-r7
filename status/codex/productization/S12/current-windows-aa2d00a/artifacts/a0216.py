"""ONE genuine H01 original max-hold EXIT test.

Proposed exit-owner API/record field assumptions are listed in companion recipe.
No TestCase fixture globals, patched E2/risk answers, financial SQL or LIVE work.
"""
import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from tests.product import test_trading_funding_v02 as funding_fixtures
from tests.product import test_trading_inventory_v02 as inventory_fixtures
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from brokers.okx_demo import stable_okx_cl_ord_id
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_state import restore_product_readback
from execution.close import prepare_close_order
from position.exit_requests import anchor_exit_request,CurrentExitAuthority,interpret_exit_request
from strategy.v02.exits import ExitRequest
from tests.product import h01_original_exit_fixture as fixtures


class H01JoinedCloseAa2d00aTests(unittest.TestCase):
    def test_original_e2_first_fill_max_hold_exit_preserves_action_and_one_close_through_partial_flat_retry(self):
        with fixtures.H01OriginalExitFixture(self) as c:
            f=c.f
            original_entry=c.entry_decision
            request=ExitRequest(json.dumps(original_entry.exit_request))
            self.assertIsNone(request.as_dict()['exit_policy']['trailing'])
            expected_anchor=anchor_exit_request(request,c.first_projection.payload,c.plan)
            self.assertEqual(c.first_fill_at,expected_anchor.first_fill_at)
            self.assertEqual(c.first_projection.payload['opened_at'],fixtures.stamp(expected_anchor.first_fill_at))
            hold_seconds=min(c.plan['protection_instruction']['max_hold_seconds'],
                request.as_dict()['exit_policy']['max_hold_seconds'])
            self.assertEqual(c.first_fill_at+timedelta(seconds=hold_seconds),expected_anchor.hold_deadline)
            self.assertLess(c.clock[0],expected_anchor.hold_deadline)
            self.assertEqual(2,len([row for row in c.provider.calls if row['method']=='POST']))
            hold_arguments=c.exit_arguments()
            held=c.runner.evaluate_original_exit(f.bundle.boundary,**hold_arguments)  # Proposed actual owner.
            self.assertEqual('HOLD',held.status)
            self.assertEqual(expected_anchor,held.anchor)
            self.assertIsNone(held.operation_id)
            self.assertIsNone(held.dispatch_outcome)
            anchor_record=f.dispatch.exit_anchor(c.service.run_id,original_entry.decision_id)
            self.assertEqual(expected_anchor,anchor_record.anchor)
            # Proposed evidence field names; values are actual earlier owner
            # records, not newest position/clock or a caller supplied anchor.
            self.assertEqual(original_entry.decision_id,anchor_record.evidence['entry_decision_id'])
            self.assertEqual(original_entry.evidence_hash,anchor_record.evidence['entry_evidence_hash'])
            self.assertEqual(c.first_projection.payload,anchor_record.evidence['source_position'])
            self.assertEqual(c.first_binding.payload,anchor_record.evidence['source_binding'])
            self.assertEqual(c.first_fill_at,anchor_record.anchor.first_fill_at)
            self.assertIsNone(f.dispatch.exit_decision(c.service.run_id,original_entry.decision_id))
            self.assertEqual(2,len([row for row in c.provider.calls if row['method']=='POST']))
            self.assertFalse(any(row.payload.get('action')=='EXIT' for row in c.recover().position_actions))

            # First-fill-derived deadline, not request/interpretation/new native
            # observation time. Expired entry proof/plan cannot revoke management.
            c.clock[0]=expected_anchor.hold_deadline
            current=c.refresh_protected()
            self.assertEqual(c.first_projection.payload['opened_at'],current.current_position_projection.payload['opened_at'])
            exit_arguments=c.exit_arguments()
            expected=interpret_exit_request(request,CurrentExitAuthority(
                current.current_position_projection.payload,c.plan,expected_anchor,
                exit_arguments['market_snapshot'],exit_arguments['market_freshness_classification'],
                c.clock[0],exit_arguments['action_expires_at']))
            self.assertEqual('AUTHORIZED',expected.status)
            self.assertEqual(('E5_MAX_HOLD_REACHED',),expected.reason_codes)
            self.assertEqual(['E5_MAX_HOLD_REACHED'],expected.position_action['reason_codes'])
            # Independent E4 oracle only computes the scripted native ACK identity.
            # It is never passed as an accepted action/request/preparation.
            expected_request=prepare_close_order(expected.position_action,c.plan,
                current.current_position_projection.payload,now=c.clock[0])
            native_client=stable_okx_cl_ord_id(expected_request.client_order_id).provider_cl_ord_id
            c.append(dict(code='0',data=[dict(ordId='3456',clOrdId=native_client,sCode='0')]))
            original_claim=f.dispatch.claim_dispatch;claims=[]
            def require_original_action_durable_before_claim(run_id,operation_id,*,lease,now):
                if operation_id==expected_request.order_request_id:
                    decision=f.dispatch.exit_decision(run_id,original_entry.decision_id)
                    self.assertEqual([dict(kind='POSITION_ACTION',payload=expected.position_action)],decision.effects)
                    actions=[row.payload for row in c.recover().position_actions
                             if row.canonical_id==expected.position_action['position_action_id']]
                    self.assertEqual([expected.position_action],actions)
                    self.assertEqual(anchor_record,f.dispatch.exit_anchor(run_id,original_entry.decision_id))
                    claims.append(operation_id)
                return original_claim(run_id,operation_id,lease=lease,now=now)

            with patch.object(f.dispatch,'claim_dispatch',side_effect=require_original_action_durable_before_claim):
                first=c.runner.evaluate_original_exit(f.bundle.boundary,**exit_arguments)
                self.assertEqual('DISPATCHED',first.status)
                self.assertEqual('ACK_PENDING',first.dispatch_outcome.status)
                self.assertEqual(expected_request.order_request_id,first.operation_id)
                self.assertEqual(expected_anchor,first.anchor)
                exit_decision=f.dispatch.exit_decision(c.service.run_id,original_entry.decision_id)
                self.assertEqual(exit_decision.decision_id,first.decision_id)
                self.assertEqual([dict(kind='POSITION_ACTION',payload=expected.position_action)],exit_decision.effects)
                original_operation=f.dispatch.operation(c.service.run_id,first.operation_id)
                close=restore_product_readback(original_operation.request)
                self.assertEqual(expected_request,close.canonical_request)
                self.assertEqual(canonical_okx_close_sizing_hash(expected.position_action),close.source_action_hash)
                self.assertEqual('EXIT_REQUESTED',c.assert_binding().current_position_projection.payload['lifecycle_state'])

                # Pass the SAME now-expired original exit arguments/read/proofs.
                # Actual claimed branch must do direct MANAGE_EXISTING GET/fills
                # before interpretation/native/expiry/new preparation gates.
                c.clock[0]+=timedelta(seconds=60)
                self.assertGreater(c.clock[0],exit_arguments['action_expires_at'])
                c.append(*c.close_responses(close,flat=False))
                before=len(c.provider.calls)
                partial_read=c.runner.evaluate_original_exit(f.bundle.boundary,**exit_arguments)
                self.assertEqual('DISPATCHED',partial_read.status)
                self.assertEqual('ORDER_OBSERVED',partial_read.dispatch_outcome.status)
                self.assertEqual(first.decision_id,partial_read.decision_id)
                self.assertEqual(first.operation_id,partial_read.operation_id)
                self.assertEqual(['GET','GET'],[row['method'] for row in c.provider.calls[before:]])
                partial=c.project_residual(close,flat=False)
                self.assertEqual(Decimal('0.0006'),Decimal(partial.current_position_projection.payload['actual_quantity']))
                self.assertEqual('EXIT_REQUESTED',partial.current_position_projection.payload['lifecycle_state'])

                # Exact duplicate readback at same actual source clock is stable;
                # its first fill ID/time/amount cannot be rewritten on retry.
                c.append(*c.close_responses(close,flat=False));before=len(c.provider.calls)
                duplicate=c.runner.evaluate_original_exit(f.bundle.boundary,**exit_arguments)
                self.assertEqual('ORDER_OBSERVED',duplicate.dispatch_outcome.status)
                self.assertEqual(['GET','GET'],[row['method'] for row in c.provider.calls[before:]])
                self.assertEqual(partial,c.assert_binding())

                c.clock[0]+=timedelta(seconds=2)
                c.append(*c.close_responses(close,flat=True))
                complete=c.runner.evaluate_original_exit(f.bundle.boundary,**exit_arguments)
                self.assertEqual('ORDER_OBSERVED',complete.dispatch_outcome.status)
                flat=c.project_residual(close,flat=True)
                self.assertEqual(Decimal(0),Decimal(flat.current_position_projection.payload['actual_quantity']))
                self.assertEqual('EXIT_REQUESTED',flat.current_position_projection.payload['lifecycle_state'])
                self.assertIsNone(flat.trade_result,'Flat is not stop cleanup/funding/final closure')
                c.append(*c.close_responses(close,flat=True));before=len(c.provider.calls)
                repeated=c.runner.evaluate_original_exit(f.bundle.boundary,**exit_arguments)
                self.assertEqual('ORDER_OBSERVED',repeated.dispatch_outcome.status)
                self.assertEqual(['GET','GET'],[row['method'] for row in c.provider.calls[before:]])
                self.assertEqual(flat,c.assert_binding())

            self.assertEqual([first.operation_id],claims)
            self.assertEqual(original_operation.request_json,f.dispatch.operation(c.service.run_id,first.operation_id).request_json)
            self.assertEqual(exit_decision,f.dispatch.exit_decision(c.service.run_id,original_entry.decision_id))
            self.assertEqual(anchor_record,f.dispatch.exit_anchor(c.service.run_id,original_entry.decision_id))
            self.assertEqual(original_entry,f.dispatch.entry_decision(c.service.run_id,f.authority.identity,f.bundle.boundary))
            posts=[row for row in c.provider.calls if row['method']=='POST']
            self.assertEqual(3,len(posts))  # Original actual ENTRY + STOP + one EXIT.
            self.assertEqual(['/api/v5/trade/order','/api/v5/trade/order-algo','/api/v5/trade/order'],
                [row['path'] for row in posts])
            self.assertTrue(posts[-1]['body']['reduceOnly'])
            self.assertFalse(c.provider._responses)
            self.assertEqual(c.provider_identity,id(c.service.provider))
            # Same original entry/exit lineage; fake-wire owner calls only.
            service=c.service;revision=c.revision
            stop_id=c.stop.canonical_request.order_request_id
            close_id=first.operation_id
            first_flat=deepcopy(flat.current_position_projection.payload)
            funding=funding_fixtures.TradingFundingV02Tests(methodName='runTest')
            funding.fixture=f.authority
            funding.flow=SimpleNamespace(position=SimpleNamespace(recover=c.recover))
            context=(service,c.provider)
            c.clock[0]+=timedelta(seconds=1)
            funding.script(context,paginated=True)
            funding_read=funding.read(context)
            funding_object=funding.publish(context,funding_read)
            self.assertEqual((funding_object,),c.recover().funding_evidence)
            self.assertEqual('0.1',funding_object.payload['funding_cost'])
            self.assertEqual(first_flat['broker_state_observed_at'],funding_object.payload['interval_end'])

            live_stop=dict(c.algo,uTime=str(int(c.clock[0].timestamp()*1000)))
            c.append(dict(code='0',data=[live_stop]),c.position_response('0',average='0'))
            target=service.read_fixture_cleanup_stop(stop_id,expected_revision=revision)
            metadata,proof=c.fresh()
            native=service.read_position(metadata=metadata,proof=proof,expected_revision=revision,
                expected_provider_position_id='5678')
            scans=inventory_fixtures.TradingInventoryV02Tests(methodName='runTest')
            c.append(*scans.scans([live_stop]))
            inventory=service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=revision)
            prepared_cleanup=service.prepare_fixture_stop_cleanup(stop_id,target,native,inventory,
                metadata=metadata,proof=proof,expected_revision=revision)
            c.append(dict(code='0',data=[dict(algoId='2345',sCode='0')]))
            service.execute_fixture_stop_cleanup(prepared_cleanup,expected_revision=revision)

            # ACK is not terminal evidence; require the real terminal readback.
            c.clock[0]+=timedelta(seconds=1)
            canceled=dict(c.algo,state='canceled',uTime=str(int(c.clock[0].timestamp()*1000)))
            c.append(dict(code='0',data=[canceled]))
            self.assertEqual('ALGO_OBSERVED',service.reconcile(stop_id,expected_revision=revision).status)
            terminal_graph=c.recover()
            self.assertEqual(first_flat,terminal_graph.current_position_projection.payload)
            self.assertIsNone(terminal_graph.trade_result)
            self.assertEqual('REINTERPRETATION_REQUIRED',terminal_graph.status)
            self.assertEqual(('E5_EXECUTION_REINTERPRETATION_REQUIRED',),terminal_graph.reason_codes)

            c.append(dict(code='0',data=[canceled]),c.position_response('0',average='0'))
            terminal=service.read_fixture_terminal_stop(stop_id,expected_revision=revision)
            metadata,proof=c.fresh()
            native=service.read_position(metadata=metadata,proof=proof,expected_revision=revision,
                expected_provider_position_id='5678')
            c.append(*scans.scans([]))
            inventory=service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=revision)
            self.assertEqual('CANCELED',terminal.status)
            self.assertEqual((),inventory.objects)
            calls=deepcopy(c.provider.calls)
            def finalize():
                return service.finalize_fixture_trade(close_id,terminal,native,inventory,
                    metadata=metadata,proof=proof,expected_revision=revision)
            receipt=finalize()
            closed=c.assert_binding()
            position=closed.current_position_projection.payload
            result=closed.trade_result.payload
            self.assertEqual('READY',closed.status)
            self.assertEqual('CLOSED',position['lifecycle_state'])
            self.assertEqual(first_flat['lifecycle_projection_id'],position['previous_lifecycle_projection_id'])
            self.assertEqual(first_flat['lifecycle_revision']+1,position['lifecycle_revision'])
            self.assertEqual(first_flat['broker_state_observed_at'],result['closed_at'])
            self.assertEqual(result['closed_at'],result['flat_position_observed_at'])
            self.assertEqual(funding_object.canonical_id,result['funding_evidence_id'])
            batch=f.dispatch.finalization_batch(service.run_id,close_id)
            self.assertIsNotNone(batch)
            self.assertEqual(receipt,f.dispatch.finalization_receipt(batch))
            self.assertEqual(receipt,finalize())
            self.assertEqual(closed,c.recover())
            self.assertEqual(calls,c.provider.calls)
            self.assertEqual(original_entry,f.dispatch.entry_decision(service.run_id,f.authority.identity,f.bundle.boundary))
            self.assertEqual(anchor_record,f.dispatch.exit_anchor(service.run_id,original_entry.decision_id))
            self.assertEqual(exit_decision,f.dispatch.exit_decision(service.run_id,original_entry.decision_id))
            self.assertEqual(original_operation.request_json,f.dispatch.operation(service.run_id,close_id).request_json)
            self.assertEqual(1,len([row for row in c.provider.calls if row['path']=='/api/v5/trade/cancel-algos']))
            self.assertEqual(4,len([row for row in c.provider.calls if row['method']=='POST']))
            self.assertFalse(c.provider._responses)
            self.assertEqual(c.provider_identity,id(service.provider))
