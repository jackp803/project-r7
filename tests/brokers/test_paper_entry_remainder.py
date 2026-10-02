"""Additive PAPER simulation of one partial entry with canceled remainder."""
from datetime import timedelta
from decimal import Decimal
import unittest

from brokers.paper import PaperBroker, InvalidOrderTransitionError
from execution.models import OrderStatus
from tests.brokers.test_paper_broker import _request


class PaperEntryRemainderTests(unittest.TestCase):
    def method(self, broker):
        self.assertTrue(hasattr(broker, 'record_entry_fill_and_cancel_remainder'),
                        'Atomic partial-entry simulation producer is missing')
        return broker.record_entry_fill_and_cancel_remainder

    def test_atomic_partial_entry_retains_one_fill_and_terminal_current_result_on_restart(self):
        request = _request(); broker = PaperBroker(); ack = broker.submit_order(request)
        fill = self.method(broker)(request.client_order_id, quantity=Decimal('.4'),
            price=Decimal('100000'), filled_at=request.created_at+timedelta(seconds=1),
            fee=Decimal('2'), fee_currency='USDT', liquidity_role='TAKER')
        restored = PaperBroker.from_state(broker.export_state())
        current = restored.query_order(request.client_order_id)
        self.assertEqual(current.order_status, OrderStatus.CANCELED)
        self.assertEqual(current.filled_quantity, Decimal('.4'))
        self.assertEqual(restored.query_fills(request.client_order_id), (fill,))
        self.assertEqual(restored.query_position(request.symbol).net_quantity, Decimal('.4'))
        self.assertEqual(broker.export_state()['payload']['submissions'][0]['acknowledgement']['order_status'], 'OPEN')
        self.assertEqual(ack.filled_quantity, 0)
        with self.assertRaises(InvalidOrderTransitionError):
            restored.record_fill(request.client_order_id, quantity=Decimal('.6'),
                price=Decimal('100000'), filled_at=request.created_at+timedelta(seconds=2))

    def test_invalid_full_zero_or_nonlater_fill_cannot_mutate_owner_state(self):
        request = _request()
        for quantity,seconds in ((Decimal('1'),1),(Decimal('0'),1),(Decimal('.4'),0)):
            with self.subTest(quantity=quantity,seconds=seconds):
                broker = PaperBroker(); broker.submit_order(request); before = broker.export_state()
                with self.assertRaises(ValueError):
                    self.method(broker)(request.client_order_id,quantity=quantity,price=Decimal('100000'),
                        filled_at=request.created_at+timedelta(seconds=seconds))
                self.assertEqual(broker.export_state(),before)

    def test_legacy_partial_cancel_still_denied_and_compound_model_cannot_rewrite_a_partial(self):
        request = _request(); broker = PaperBroker(); broker.submit_order(request)
        broker.record_fill(request.client_order_id,quantity=Decimal('.4'),price=Decimal('100000'),
            filled_at=request.created_at+timedelta(seconds=1))
        before = broker.export_state()
        with self.assertRaises(InvalidOrderTransitionError):
            broker.cancel_order(request.client_order_id,observed_at=request.created_at+timedelta(seconds=2))
        with self.assertRaises(ValueError):
            self.method(broker)(request.client_order_id,quantity=Decimal('.4'),price=Decimal('100000'),
                filled_at=request.created_at+timedelta(seconds=2))
        self.assertEqual(broker.export_state(),before)


if __name__ == '__main__': unittest.main()
