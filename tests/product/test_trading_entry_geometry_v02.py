"""Actual caller geometry must remain bound to the real E2 exit request."""
import unittest
from dataclasses import replace
from decimal import Decimal

from application.trading.orchestrator import TradingOrchestrator
from risk.engine import evaluate_trade_intent
from storage.product_dispatch import ProductDispatchError
from tests.product.h01_entry_fixture import H01EntryFixture


class TradingEntryGeometryV02Tests(unittest.TestCase):
    def test_policy_valid_alternative_prices_cannot_replace_actual_e2_geometry(self):
        with H01EntryFixture() as f:
            proposal = replace(f.proposal,
                required_stop_level=f.proposal.required_stop_level-Decimal('1'),
                required_target_level=f.proposal.required_target_level+Decimal('1'))
            decision = evaluate_trade_intent(f.intent, f.context, proposal,
                f.selected.risk_policy, decided_at=f.now)
            self.assertEqual('APPROVE', decision['decision'], decision['reason_codes'])
            arguments = dict(f.arguments, risk_proposal=proposal)
            with self.assertRaisesRegex(ProductDispatchError, 'ENTRY_E2_GEOMETRY_PROPOSAL_MISMATCH'):
                TradingOrchestrator(f.service).evaluate_entry(f.bundle, **arguments)
            self.assertEqual([], f.provider.calls)
            self.assertIsNone(f.dispatch.entry_decision(f.service.run_id,
                f.authority.identity, f.bundle.boundary))
            recovered = f.canonical.recover(trade_plan_id=f.plan['trade_plan_id'])
            self.assertIsNone(recovered.risk_decision)
            self.assertIsNone(recovered.approved_trade_plan)
