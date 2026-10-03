import unittest
from dataclasses import replace
from decimal import Decimal

import tests.brokers.test_okx_product_translation_v02 as entry_fixtures
import tests.brokers.test_okx_product_protection_v02 as stop_fixtures
from execution.models import OrderStatus


class OKXProductReadbackV02Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = entry_fixtures.OKXProductTranslationV02Tests(methodName='runTest')
        self.fixture.setUp()
        self.prepared = self.fixture.entry()
        self.materialized = self.prepared.materialization
        self.now = self.fixture.now

    def order(self, **changes):
        body = dict(self.materialized.body)
        body.update(instType='SWAP', ordId='1234', state='live', accFillSz='0', avgPx='0', reduceOnly='false')
        body.update(changes)
        return {'code': '0', 'data': [body]}

    def test_success_ack_is_pending_without_fill_and_errors_are_sanitized(self):
        from brokers.okx_product_readback import parse_product_ack
        response = dict(code='0', data=[dict(clOrdId=self.materialized.provider_cl_ord_id, ordId='1234', sCode='0')])
        result = parse_product_ack(response, self.prepared, observed_at=self.now)
        self.assertEqual(OrderStatus.PENDING, result.order_status)
        self.assertEqual(Decimal('0'), result.filled_quantity)
        response['data'][0].update(sCode='51000', sMsg='private fake credential account payload')
        result = parse_product_ack(response, self.prepared, observed_at=self.now)
        self.assertEqual('PROVIDER_ORDER_REJECTED', result.reject_reason)
        response['data'][0]['ordId'] = 'private fake credential account payload'
        result = parse_product_ack(response, self.prepared, observed_at=self.now)
        self.assertIsNone(result.broker_order_id)

    def test_current_order_fields_and_partial_fill_are_strictly_bound(self):
        from brokers.okx_product_readback import parse_product_order
        live = parse_product_order(self.order(), self.prepared, observed_at=self.now, expected_provider_id='1234')
        self.assertEqual(OrderStatus.OPEN, live.result.order_status)
        partial = parse_product_order(self.order(state='partially_filled', accFillSz='4', avgPx='60000'),
                        self.prepared, observed_at=self.now, expected_provider_id='1234')
        self.assertEqual(Decimal('0.004'), partial.result.filled_quantity)
        for changes in ({'tdMode': 'cross'}, {'posSide': 'long'}, {'side': 'sell'}, {'ordType': 'limit'},
                        {'reduceOnly': 'true'}, {'ordId': '999'}, {'sz': '11'}, {'instId': 'ETH-USDT-SWAP'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_product_order(self.order(**changes), self.prepared, observed_at=self.now, expected_provider_id='1234')

    def test_success_empty_or_provider_error_never_proves_absence(self):
        from brokers.okx_product_readback import parse_product_order
        for response in ({'code': '0', 'data': []}, {'code': '51603', 'data': []}):
            result = parse_product_order(response, self.prepared, observed_at=self.now, expected_provider_id='1234')
            self.assertFalse(result.found)
            self.assertIn('NOT_ABSENCE_PROOF', result.lookup_status)

    def test_duplicate_wrong_order_or_wrong_side_fills_fail_closed_and_fee_sign_survives(self):
        from brokers.okx_product_readback import parse_product_fills
        fill = dict(instId='BTC-USDT-SWAP', clOrdId=self.materialized.provider_cl_ord_id,
                    ordId='1234', tradeId='1', side='buy', posSide='net', fillSz='4', fillPx='60000',
                    fillTime=str(int(self.now.timestamp() * 1000)), fee='-0.12', feeCcy='USDT')
        result = parse_product_fills({'code': '0', 'data': [fill]}, self.prepared, expected_provider_id='1234')
        self.assertEqual(Decimal('0.004'), result[0].quantity)
        self.assertEqual(Decimal('-0.12'), result[0].fee)
        for rows in ([fill, fill], [dict(fill, ordId='999')], [dict(fill, side='sell')]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                parse_product_fills({'code': '0', 'data': rows}, self.prepared, expected_provider_id='1234')

    def stop(self):
        fixture = stop_fixtures.OKXProductProtectionV02Tests(methodName='runTest')
        fixture.setUp()
        context = fixture.context()
        return fixture.translator.prepare_protection(**context), context['now']

    def algo(self, prepared, **changes):
        row = dict(prepared.materialization.body)
        row.update(instType='SWAP', algoId='2345', state='live', reduceOnly='true',
                   ordIdList=[], ordId='', actualSz='0', actualPx='', failCode='')
        row.update(changes)
        return {'code': '0', 'data': [row]}

    def test_algo_ack_and_native_live_triggered_states_do_not_invent_fill_or_flatness(self):
        from brokers.okx_product_readback import parse_product_ack, parse_product_algo
        prepared, now = self.stop()
        ack = parse_product_ack({'code': '0', 'data': [dict(algoId='2345', algoClOrdId=prepared.materialization.provider_cl_ord_id, sCode='0')]},
                                 prepared, observed_at=now)
        self.assertEqual(OrderStatus.PENDING, ack.order_status)
        live = parse_product_algo(self.algo(prepared), prepared, expected_provider_id='2345')
        self.assertEqual('ACTIVE', live.status)
        triggered = parse_product_algo(self.algo(prepared, state='effective', ordIdList=['3456'], ordId='3456', actualSz='12'),
                                         prepared, expected_provider_id='2345')
        self.assertEqual('TRIGGERED_REQUIRES_CHILD_ORDER', triggered.status)
        self.assertEqual(('3456',), triggered.child_order_ids)
        self.assertFalse(hasattr(triggered, 'filled_quantity'))

    def test_algo_wrong_basis_duplicates_or_unbound_child_order_are_not_active(self):
        from brokers.okx_product_readback import parse_product_algo
        prepared, _ = self.stop()
        for changes in ({'slTriggerPxType': 'mark'}, {'slOrdPx': '59900'}, {'reduceOnly': 'false'},
                        {'ordIdList': ['1', '1']}, {'state': 'live', 'ordIdList': ['1']}, {'algoId': '999'},
                        {'state': 'effective', 'ordIdList': ['1', '2']}, {'actualSz': '13'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_product_algo(self.algo(prepared, **changes), prepared, expected_provider_id='2345')

    def child(self, prepared, now, **changes):
        body = dict(prepared.materialization.body)
        body = {key: body[key] for key in ('instId', 'tdMode', 'posSide', 'side', 'sz', 'reduceOnly')}
        body.update(instType='SWAP', ordType='market', clOrdId='CHILD123', ordId='3456',
                    state='partially_filled', accFillSz='4', avgPx='60000')
        body.update(changes)
        fill = dict(instId='BTC-USDT-SWAP', clOrdId='CHILD123', ordId='3456', tradeId='1',
                    side=body['side'], posSide='net', fillSz='4', fillPx='60000',
                    fillTime=str(int(now.timestamp() * 1000)), fee='-0.12', feeCcy='USDT')
        return dict(code='0', data=[body]), dict(code='0', data=[fill])

    def test_stop_child_has_native_child_identity_and_parent_canonical_action_lineage(self):
        from brokers.okx_product_readback import parse_product_stop_child
        prepared, now = self.stop()
        order, fills = self.child(prepared, now)
        outcome = parse_product_stop_child(
            self.algo(prepared, state='effective', ordIdList=['3456'], ordId='3456', actualSz='4'),
            order, fills, prepared, observed_at=now, expected_provider_id='2345')
        self.assertEqual('2345', outcome.parent_result.broker_order_id)
        self.assertEqual(OrderStatus.PARTIALLY_FILLED, outcome.parent_result.order_status)
        self.assertEqual('3456', outcome.child_result.broker_order_id)
        self.assertEqual('3456', outcome.fills[0].broker_order_id)
        self.assertEqual(prepared.canonical_request.client_order_id, outcome.fills[0].client_order_id)
        for field in ('position_action_id', 'position_id', 'order_role'):
            self.assertEqual(getattr(prepared.canonical_request, field), getattr(outcome.fills[0], field))
        expected_quantity = prepared.materialization.effective_canonical_quantity / prepared.materialization.provider_contract_quantity * 4
        self.assertEqual(expected_quantity, outcome.parent_result.filled_quantity)

    def test_stop_child_requires_complete_consistent_exact_child_and_fill_truth(self):
        from brokers.okx_product_readback import parse_product_stop_child
        prepared, now = self.stop()
        algo = self.algo(prepared, state='effective', ordIdList=['3456'], ordId='3456', actualSz='4')
        order, fills = self.child(prepared, now)
        for changes in ({'ordId': '999'}, {'reduceOnly': False}, {'side': 'buy'},
                        {'tdMode': 'cross'}, {'sz': '13'}, {'clOrdId': 'private payload'},
                        {'accFillSz': '5'}, {'avgPx': '60001'}):
            changed, _ = self.child(prepared, now, **changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_product_stop_child(algo, changed, fills, prepared, observed_at=now, expected_provider_id='2345')
        for rows in ([], fills['data'] * 2, [dict(fills['data'][0], ordId='999')],
                     [dict(fills['data'][0], clOrdId='OTHER')]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                parse_product_stop_child(algo, order, dict(code='0', data=rows), prepared,
                                         observed_at=now, expected_provider_id='2345')
        with self.assertRaises(ValueError):
            parse_product_stop_child(self.algo(prepared), order, fills, prepared,
                                     observed_at=now, expected_provider_id='2345')


if __name__ == '__main__':
    unittest.main()
