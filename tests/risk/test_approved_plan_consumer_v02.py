import unittest
from datetime import datetime, timezone
from decimal import Decimal
from copy import deepcopy
from risk.engine import RiskContext, RiskProposal, evaluate_trade_intent, build_approved_trade_plan
from risk.product_policy import parse_product_risk_policy
import tests.application.test_product_assessment_binding as fixtures


def approved(identity, now):
    policy = parse_product_risk_policy(fixtures.risk_fixture(), namespace='FIXTURE').risk_policy
    intent = dict(schema_version='contracts-v0.1', intent_id='runtime-intent', signal_id='runtime-signal',
                  strategy_id=identity.strategy_id, strategy_version=identity.strategy_version,
                  symbol='BTC_USDT_PERP', direction='LONG', generated_at=now.isoformat().replace('+00:00', 'Z'),
                  market_boundary_ref='fixture-market-boundary', entry_profile_version='entry-v0.1',
                  entry_order_type='MARKET', entry_reference_price='60000')
    context = RiskContext('HEALTHY', True, 'KNOWN', True, 'FLAT', True, 'KNOWN', True,
                          False, True, 0, 0, False, 0, Decimal('0'), Decimal('100'))
    proposal = RiskProposal(Decimal('0.001'), Decimal('60'), Decimal('60'), Decimal('1'),
                           Decimal('0.6'), Decimal('0'), Decimal('0.6'), Decimal('59400'), Decimal('60600'))
    risk = evaluate_trade_intent(intent, context, proposal, policy, decided_at=now)
    plan = build_approved_trade_plan(intent, risk, policy, created_at=now)
    return risk, plan, policy


class ApprovedPlanConsumerV02Tests(unittest.TestCase):
    def setUp(self):
        from registry import StrategyIdentity
        self.risk, self.plan, self.policy = approved(StrategyIdentity('strategy', '1.0.0'), datetime(2026, 10, 3, tzinfo=timezone.utc))

    def consume(self, risk=None, plan=None):
        from risk.engine import require_approved_trade_plan_binding
        return require_approved_trade_plan_binding(self.risk if risk is None else risk,
                                                   self.plan if plan is None else plan, self.policy)

    def test_actual_e5_approval_and_plan_are_consumed_without_rebuilding_intent(self):
        self.assertEqual('APPROVE', self.risk['decision'])
        self.consume()

    def test_other_risk_lineage_or_enlarged_bounds_are_rejected(self):
        for field, value in (('risk_decision_id', 'other'), ('intent_id', 'other'), ('strategy_version', 'other'),
                             ('quantity', '0.002'), ('leverage', '2'), ('margin_mode', 'CROSS')):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.consume(plan=dict(self.plan, **{field: value}))
        plan = deepcopy(self.plan)
        plan['protection_instruction']['stop_level'] = '59000'
        with self.assertRaises(ValueError): self.consume(plan=plan)

    def test_unsafe_approval_or_current_policy_caps_cannot_be_consumed(self):
        for field, value in (('decision', 'REJECT'), ('market_health_status', 'UNKNOWN'),
                             ('reason_codes', ['DENIED']), ('approved_notional', '101'), ('approved_margin', '101'),
                             ('approved_leverage', '2'), ('max_hold_seconds', 3601)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.consume(risk=dict(self.risk, **{field: value}))

    def test_loss_estimate_must_be_finite_and_nonnegative_before_financial_comparison(self):
        for value in ('NaN', 'Infinity', '-0.01', True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as rejected:
                    self.consume(risk=dict(self.risk, estimated_max_loss=value))
                self.assertEqual('EXACT_APPROVED_PLAN_BINDING_REQUIRED', rejected.exception.code)


if __name__ == '__main__': unittest.main()
