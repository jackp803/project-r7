"""E4 rejection inputs retain real submissions/fills and existing state codec."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import unittest
from brokers.paper import PaperBroker
from execution.models import OrderStatus
from tests.brokers import test_paper_broker_protection_terminal as fixture


class FixtureProtectionRejectionTests(unittest.TestCase):
    setUp=fixture.PaperBrokerProtectionTerminalTests.setUp
    _entry_request=fixture.PaperBrokerProtectionTerminalTests._entry_request
    _protection_request=fixture.PaperBrokerProtectionTerminalTests._protection_request

    def filled(self):
        request=self._protection_request(quantity='0.002')
        entry=replace(self._entry_request(),trade_plan_id=request.trade_plan_id)
        broker=PaperBroker();broker.submit_order(entry)
        broker.record_fill(entry.client_order_id,quantity=entry.quantity,price=Decimal('60000'),
            filled_at=self.now+timedelta(seconds=1))
        return broker,entry,replace(request,created_at=self.now+timedelta(seconds=1))

    def test_actual_first_protection_rejection_retains_fills_and_roundtrips_existing_codec(self):
        broker,entry,request=self.filled();before=broker.query_fills(entry.client_order_id)
        broker.reject_fixture_protection_submission(request,namespace='FIXTURE')
        result=broker.submit_order(request)
        self.assertEqual(result.order_status,OrderStatus.REJECTED)
        self.assertEqual(broker.query_position(request.symbol).net_quantity,entry.quantity)
        self.assertEqual(broker.query_fills(entry.client_order_id),before)
        self.assertEqual(broker.query_fills(request.client_order_id),())
        restored=PaperBroker.from_state(broker.export_state())
        self.assertEqual(restored.query_order(request.client_order_id),result)
        self.assertEqual(restored.query_fills(entry.client_order_id),before)

    def test_fault_cannot_target_entry_ordinary_namespace_absent_fill_or_existing_order(self):
        broker,entry,request=self.filled();original=broker.export_state()
        for candidate,namespace in ((entry,'FIXTURE'),(request,'LOCAL_RESEARCH'),
                (replace(request,quantity=Decimal('1')),'FIXTURE')):
            with self.subTest(namespace=namespace),self.assertRaises(ValueError):
                broker.reject_fixture_protection_submission(candidate,namespace=namespace)
            self.assertEqual(broker.export_state(),original)
        with self.assertRaises(ValueError):PaperBroker().reject_fixture_protection_submission(request,namespace='FIXTURE')
        broker.submit_order(request);original=broker.export_state()
        with self.assertRaises(ValueError):broker.reject_fixture_protection_submission(request,namespace='FIXTURE')
        self.assertEqual(broker.export_state(),original)


if __name__=='__main__':unittest.main()
