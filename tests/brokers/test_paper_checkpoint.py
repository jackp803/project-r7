import copy
import hashlib
import json
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from brokers.paper import (
    IdempotencyConflictError, PaperBroker, ReconciliationRequiredError,
)
from execution.models import OrderStatus
from tests.brokers.test_paper_broker import _request


def _roundtrip(broker):
    return PaperBroker.from_state(json.loads(json.dumps(broker.export_state())))


def _rehash(state):
    state['payload_hash'] = hashlib.sha256(json.dumps(
        state['payload'], sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False,
    ).encode('utf-8')).hexdigest()
    return state


class PaperCheckpointTests(unittest.TestCase):
    def test_restart_retains_partial_fill_first_time_and_no_duplicate_submission(self):
        request = _request()
        broker = PaperBroker()
        broker.submit_order(request)
        first = broker.record_fill(request.client_order_id, quantity=Decimal('.4'),
            price=Decimal('100000'), filled_at=request.created_at + timedelta(minutes=1),
            fee=Decimal('2'), fee_currency='USDT', liquidity_role='TAKER')
        restored = _roundtrip(broker)
        self.assertEqual(restored.query_position(request.symbol).net_quantity, Decimal('.4'))
        self.assertEqual(restored.query_fills(request.client_order_id), (first,))
        self.assertEqual(restored.submit_order(request).order_status, OrderStatus.PARTIALLY_FILLED)
        with self.assertRaises(IdempotencyConflictError):
            restored.submit_order(replace(request, quantity=Decimal('2')))
        restored.record_fill(request.client_order_id, quantity=Decimal('.6'),
            price=Decimal('110000'), filled_at=request.created_at + timedelta(minutes=4))
        current = restored.query_order(request.client_order_id)
        self.assertEqual(current.filled_quantity, Decimal('1'))
        self.assertEqual(current.average_fill_price, Decimal('106000'))
        self.assertEqual(restored.query_fills(request.client_order_id)[0].filled_at,
                         request.created_at + timedelta(minutes=1))
        self.assertEqual(broker.query_position(request.symbol).net_quantity, Decimal('.4'))

    def test_restart_retains_ambiguous_ack_separate_from_actual_filled_order(self):
        request = _request()
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: True})
        ack = broker.submit_order(request)
        broker.record_fill(request.client_order_id, quantity=Decimal('1'),
            price=Decimal('100000'), filled_at=request.created_at + timedelta(minutes=1))
        restored = _roundtrip(broker)
        self.assertEqual(restored.submit_order(request), ack)
        self.assertEqual(restored.query_order(request.client_order_id).order_status, OrderStatus.FILLED)
        proof = restored.reconcile(request, order_snapshot=restored.query_order(request.client_order_id),
                                   position_snapshot=restored.query_position(request.symbol))
        self.assertFalse(proof.retry_allowed)
        self.assertEqual(restored.query_position(request.symbol).net_quantity, Decimal('1'))

    def test_pre_restart_retry_permission_requires_new_explicit_reconciliation(self):
        request = _request()
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: False})
        broker.submit_order(request)
        old = broker.reconcile(request, order_snapshot=None,
                               position_snapshot=broker.query_position(request.symbol))
        restored = _roundtrip(broker)
        with self.assertRaises(ReconciliationRequiredError):
            restored.retry_order(request, reconciliation=old)
        fresh = restored.reconcile(request, order_snapshot=restored.query_order(request.client_order_id),
                                   position_snapshot=restored.query_position(request.symbol))
        self.assertTrue(fresh.retry_allowed)
        self.assertEqual(restored.retry_order(request, reconciliation=fresh).order_status, OrderStatus.OPEN)
        self.assertEqual(restored.query_position(request.symbol).net_quantity, Decimal('0'))

    def test_terminal_orders_do_not_reopen_on_restart(self):
        request = _request()
        for status in ('CANCELED', 'EXPIRED', 'REJECTED'):
            with self.subTest(status=status):
                broker = PaperBroker(rejected_outcomes={request.client_order_id: 'FIXTURE_REJECT'}
                                     if status == 'REJECTED' else None)
                broker.submit_order(request)
                if status != 'REJECTED':
                    getattr(broker, 'cancel_order' if status == 'CANCELED' else 'expire_order')(
                        request.client_order_id, observed_at=request.created_at + timedelta(minutes=1))
                restored = _roundtrip(broker)
                self.assertEqual(restored.submit_order(request).order_status.value, status)
                self.assertEqual(restored.query_position(request.symbol).net_quantity, Decimal('0'))

    def test_future_simulation_controls_survive_without_replaying_orders(self):
        request = _request()
        restored = _roundtrip(PaperBroker(ambiguous_outcomes={request.client_order_id: False}))
        self.assertEqual(restored.submit_order(request).order_status, OrderStatus.RECONCILIATION_REQUIRED)
        self.assertIsNone(restored.query_order(request.client_order_id))

    def test_corrupt_hash_and_unrecognized_snapshot_fields_fail_closed(self):
        state = PaperBroker().export_state()
        for changed in (dict(state, payload_hash='0' * 64), dict(state, credentials='forbidden')):
            with self.subTest(changed=tuple(changed)):
                with self.assertRaises(ValueError):
                    PaperBroker.from_state(changed)

    def test_rehashed_inconsistent_fill_quantity_lineage_and_duplicate_orders_rejected(self):
        request = _request()
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(request.client_order_id, quantity=Decimal('.4'),
            price=Decimal('100000'), filled_at=request.created_at + timedelta(minutes=1))
        original = broker.export_state()
        alterations = (
            lambda p: p['submissions'][0]['order']['result'].__setitem__('filled_quantity', '.5'),
            lambda p: p['submissions'][0]['order']['fills'][0].__setitem__('trade_plan_id', 'different'),
            lambda p: p['submissions'].append(copy.deepcopy(p['submissions'][0])),
            lambda p: p['submissions'][0]['request'].__setitem__('quantity', 'NaN'),
            lambda p: p['submissions'][0]['order']['fills'][0].__setitem__('filled_at', '2026-08-21T00:01:00'),
            lambda p: p['submissions'][0]['request'].__setitem__('reduce_only', 'false'),
        )
        for mutate in alterations:
            changed = copy.deepcopy(original)
            mutate(changed['payload'])
            with self.subTest(mutation=alterations.index(mutate)):
                with self.assertRaises(ValueError):
                    PaperBroker.from_state(_rehash(changed))


if __name__ == '__main__':
    unittest.main()
