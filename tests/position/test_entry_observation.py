import importlib.util
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from brokers.paper import PaperBroker
from execution.gateway import ExecutionGateway
from execution.models import PositionExposureSnapshot
from tests.storage.test_paper_runtime_durability import approved_plan

NOW = datetime(2026, 8, 24, 7, 0, 10, tzinfo=timezone.utc)


class EntryObservationTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('position.entry_observation'),
                             'E5 projection from actual Paper entry observations is missing')
        from position.entry_observation import build_entry_projection
        return build_entry_projection

    def filled(self):
        plan = approved_plan()
        broker = PaperBroker()
        request = ExecutionGateway().prepare_entry_order(plan, now=NOW - timedelta(seconds=1))
        broker.submit_order(request)
        broker.record_fill(request.client_order_id, quantity=Decimal('.0012'), price=Decimal('60000'), filled_at=NOW)
        return plan, broker, request

    def test_partial_fill_uses_actual_owner_evidence_and_canonical_entry_transition(self):
        build = self.api()
        plan, broker, request = self.filled()
        result = build(plan, request, broker.query_order(request.client_order_id),
            broker.query_fills(request.client_order_id), broker.query_position(request.symbol), observed_at=NOW)
        self.assertEqual(len(result.projections), 2)
        self.assertEqual(result.projections[0].lifecycle_projection['lifecycle_state'], 'PENDING_ENTRY')
        opened = result.projections[1].lifecycle_projection
        self.assertEqual(opened['lifecycle_state'], 'OPEN_UNPROTECTED')
        self.assertEqual(opened['lifecycle_event'], 'ENTRY_FILL_OBSERVED')
        self.assertEqual(opened['actual_quantity'], '0.0012')
        self.assertEqual(opened['opened_at'], '2026-08-24T07:00:10Z')
        self.assertEqual(opened['average_entry_price'], '60000')

    def test_later_partial_fill_preserves_first_fill_and_requires_reattestation(self):
        build = self.api()
        plan, broker, request = self.filled()
        first = build(plan, request, broker.query_order(request.client_order_id),
            broker.query_fills(request.client_order_id), broker.query_position(request.symbol), observed_at=NOW)
        broker.record_fill(request.client_order_id, quantity=Decimal('.0018'), price=Decimal('61000'), filled_at=NOW + timedelta(seconds=20))
        later = build(plan, request, broker.query_order(request.client_order_id),
            broker.query_fills(request.client_order_id), broker.query_position(request.symbol),
            observed_at=NOW + timedelta(seconds=20), previous_projection=first.projections[-1].lifecycle_projection)
        self.assertEqual(len(later.projections), 1)
        current = later.projections[0].lifecycle_projection
        self.assertEqual(current['opened_at'], '2026-08-24T07:00:10Z')
        self.assertEqual(Decimal(current['actual_quantity']), Decimal('0.003'))
        self.assertEqual(Decimal(current['average_entry_price']), Decimal('60600'))
        self.assertEqual(current['lifecycle_revision'], 2)
        self.assertEqual(current['lifecycle_state'], 'OPEN_UNPROTECTED')
        self.assertEqual(current['lifecycle_projection_kind'], 'REATTESTATION')

    def test_unknown_net_position_future_fill_or_wrong_parent_cannot_invent_exposure(self):
        build = self.api()
        plan, broker, request = self.filled()
        for position, at, parent in (
            (PositionExposureSnapshot(request.symbol, Decimal('0')), NOW, plan),
            (broker.query_position(request.symbol), NOW - timedelta(seconds=1), plan),
            (broker.query_position(request.symbol), NOW, dict(plan, trade_plan_id='wrong')),
        ):
            with self.subTest(at=at, parent=parent['trade_plan_id']), self.assertRaises(ValueError):
                build(parent, request, broker.query_order(request.client_order_id),
                      broker.query_fills(request.client_order_id), position, observed_at=at)

    def test_inconsistent_average_price_cannot_change_actual_entry_basis(self):
        build = self.api()
        plan, broker, request = self.filled()
        changed = replace(broker.query_order(request.client_order_id), average_fill_price=Decimal('70000'))
        with self.assertRaises(ValueError):
            build(plan, request, changed, broker.query_fills(request.client_order_id),
                  broker.query_position(request.symbol), observed_at=NOW)

    def test_later_fill_outgrowing_verified_protection_enters_canonical_emergency(self):
        from position import (build_protect_position_action, interpret_protection_result,
                              ProtectionResultEvidence)
        from execution.protection import prepare_protection_order
        from position.lifecycle_execution_binding import build_position_lifecycle_transition_with_execution_binding
        from position.lifecycle_projection import _broker_fact_payload
        build = self.api()
        plan, broker, request = self.filled()
        first = build(plan, request, broker.query_order(request.client_order_id),
            broker.query_fills(request.client_order_id), broker.query_position(request.symbol), observed_at=NOW)
        opened = first.projections[-1].lifecycle_projection
        at = NOW + timedelta(seconds=1)
        action = build_protect_position_action(opened, plan, created_at=at, expires_at=at+timedelta(seconds=30))
        protect = prepare_protection_order(action, plan, opened, now=at)
        ack = broker.submit_order(protect)
        interpretation = interpret_protection_result(protect,
            ProtectionResultEvidence(True, broker.query_order(protect.client_order_id), ack), opened['lifecycle_state'])
        self.assertTrue(interpretation.protection_verified)
        source = dict(_broker_fact_payload(opened), lifecycle_state=opened['lifecycle_state'])
        protected = build_position_lifecycle_transition_with_execution_binding(source, opened,
            lifecycle_event=interpretation.event, lifecycle_interpreted_at=at,
            order_requests=(request, protect), order_results=(ack,), fills=broker.query_fills(request.client_order_id))
        at += timedelta(seconds=1)
        broker.record_fill(request.client_order_id, quantity=Decimal('.0018'), price=Decimal('60000'), filled_at=at)
        later = build(plan, request, broker.query_order(request.client_order_id),
            broker.query_fills(request.client_order_id), broker.query_position(request.symbol),
            observed_at=at, previous_projection=protected.lifecycle_projection)
        current = later.projections[-1].lifecycle_projection
        self.assertEqual(current['lifecycle_state'], 'EMERGENCY')
        self.assertEqual(current['lifecycle_event'], 'PROTECTION_LOST')
        self.assertEqual(Decimal(current['actual_quantity']), Decimal('.003'))


if __name__ == '__main__': unittest.main()
