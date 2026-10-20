"""Genuine original cleanup then terminal GET; no finalization credit."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_stop_cleanup_v02 as cleanup_fixtures


class TradingTerminalStopV02Tests(unittest.TestCase):
    def settled(self):
        h=cleanup_fixtures.TradingStopCleanupV02Tests(methodName='runTest')
        h.setUp();self.addCleanup(h.doCleanups)
        h.flat();preparation=h.prepare(h.reads())
        h.flow.append(dict(code='0',data=[dict(algoId='2345',sCode='0')]))
        h.execute(preparation)
        stop_id=h.flow.stop.canonical_request.order_request_id
        h.fixture.clock[0]+=timedelta(seconds=1)
        row=h.algo(state='canceled')
        h.flow.append(dict(code='0',data=[row]))
        self.assertEqual('ALGO_OBSERVED',h.service.reconcile(stop_id,expected_revision=h.fixture.revision).status)
        return h,row

    def test_original_canonical_cancel_and_current_target_issue_only_detached_terminal_fact(self):
        h,row=self.settled();stop_id=h.flow.stop.canonical_request.order_request_id
        before=h.flow.recover();before_calls=len(h.provider.calls)
        self.assertIsNone(before.trade_result)
        self.assertEqual('EXIT_REQUESTED',before.current_position_projection.payload['lifecycle_state'])
        with patch.object(h.service.dispatch,'stop_cleanup_claim',return_value=None):
            with self.assertRaises(ValueError):
                h.service.read_fixture_terminal_stop(stop_id,expected_revision=h.fixture.revision)
        self.assertEqual(before_calls,len(h.provider.calls))
        self.assertEqual({},h.service._terminal_stop_reads)
        h.flow.append(dict(code='0',data=[row]))
        value=h.service.read_fixture_terminal_stop(stop_id,expected_revision=h.fixture.revision)
        self.assertEqual('CANCELED',value.status)
        self.assertEqual(stop_id,value.operation_id)
        self.assertEqual(h.flow.close.canonical_request.order_request_id,value.close_operation_id)
        self.assertEqual('2345',value.observation.provider_algo_id)
        self.assertEqual(row,json.loads(value.observation.row_json))
        self.assertEqual(before,h.flow.recover())
        self.assertEqual(1,len(h.cancel_calls()))
        calls=h.provider.calls[before_calls:]
        self.assertEqual([('GET','/api/v5/trade/order-algo',dict(algoId='2345'))],
                         [(x['method'],x['path'],x['query']) for x in calls])
        from application.trading.terminal_stop import require_terminal_stop_read
        require_terminal_stop_read(h.service,value,stop_id)
        with self.assertRaises(ValueError):require_terminal_stop_read(h.service,replace(value),stop_id)
        from application.trading.provider import FakeProductProvider
        h.service.provider=FakeProductProvider([])
        try:
            with self.assertRaises(ValueError):require_terminal_stop_read(h.service,value,stop_id)
        finally:h.service.provider=h.provider
        original_subject=h.service.canonical.require_current_execution_subject;replaced=[]
        original_lease=h.service.lease;original_record=h.service._terminal_stop_reads[id(value)]
        for mutation in ('provider','lease','cache','claim'):
            def source_then_replace(*args,**kwargs):
                result=original_subject(*args,**kwargs)
                if mutation=='provider':h.service.provider=FakeProductProvider([])
                elif mutation=='lease':h.service.lease=replace(original_lease,instance_id='replacement-process')
                elif mutation=='cache':h.service._terminal_stop_reads[id(value)]=tuple(list(original_record))
                else:h.append_unknown_entry()
                replaced.append(mutation);return result
            try:
                with self.subTest(mutation=mutation),patch.object(type(h.service.canonical),'require_current_execution_subject',side_effect=source_then_replace):
                    with self.assertRaises(ValueError):require_terminal_stop_read(h.service,value,stop_id)
            finally:
                h.service.provider=h.provider;h.service.lease=original_lease
                h.service._terminal_stop_reads[id(value)]=original_record
        self.assertEqual(['provider','lease','cache','claim'],replaced)
        h.fixture.clock[0]+=timedelta(seconds=6)
        with self.assertRaises(ValueError):require_terminal_stop_read(h.service,value,stop_id)
        self.assertEqual(before,h.flow.recover())
        self.assertFalse(h.provider._responses)

    def test_actual_other_connection_claim_after_target_get_denies_issuance(self):
        h,row=self.settled();stop_id=h.flow.stop.canonical_request.order_request_id
        before=h.flow.recover();calls=len(h.provider.calls);original=h.provider.request;appended=[]
        h.flow.append(dict(code='0',data=[row]))
        def read_then_append(*args,**kwargs):
            value=original(*args,**kwargs)
            if not appended:
                h.append_unknown_entry();appended.append(True)
            return value
        with patch.object(h.provider,'request',side_effect=read_then_append):
            with self.assertRaises(ValueError):
                h.service.read_fixture_terminal_stop(stop_id,expected_revision=h.fixture.revision)
        self.assertTrue(appended)
        self.assertEqual({},h.service._terminal_stop_reads)
        self.assertEqual(before,h.flow.recover())
        self.assertEqual(1,len(h.cancel_calls()))
        self.assertEqual([('GET','/api/v5/trade/order-algo')],
            [(x['method'],x['path']) for x in h.provider.calls[calls:]])
        self.assertFalse(h.provider._responses)
