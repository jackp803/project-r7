"""Actual joined entry regression. Non-TestCase H01 fixture; no acceptance credit.

Intended eventual path: tests/product/h01_entry_fixture.py.
Uses real registered strategy/E6/E7 fixture owners. All observations/context below
are explicit synthetic test vectors, not production balance/health defaults.
Never imports the authored-intent risk_fixtures.approved helper.
"""
import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from tests.product import test_live_admission_v02 as admission_fixtures
from tests.brokers import test_okx_demo_adapter as metadata_fixtures
from application.trading.admission import RuntimeAdmission
from application.trading.service import TradingService
from application.trading.provider import FakeProductProvider
from brokers.okx_demo import OKXAccountConfigSnapshot, OKXPrerequisiteSnapshot
from brokers.okx_product import OKXProductTranslator
from brokers.okx_product_capability import OKXProductCapabilityOwner
from market_data.candle import Candle
from position.exit_requests import resolve_exit_constraints
from risk.engine import RiskContext, RiskProposal, evaluate_trade_intent, build_approved_trade_plan
from risk.product_policy import parse_product_risk_policy
from storage.product_dispatch import open_product_dispatch_journal
from storage.runtime import open_paper_runtime_journal
from strategy import StrategyRuntime, parse_strategy_definition, build_trade_intent
from strategy.v02.temporal import build_asof_bundle
from strategy.v02.exits import build_exit_request


class H01EntryFixture:
    """Owns existing TestCase fixture cleanup, but is not a discoverable TestCase."""
    def __enter__(self):
        self.authority = admission_fixtures.LiveAdmissionV02Tests(methodName='runTest')
        self.dispatch = self.canonical = None
        try:
            self.authority.setUp()
            owner = self.authority
            self.now = owner.clock[0]  # Existing fixture: 2026-10-03T00:00:00Z.
            self.record = owner.e6.get_strategy(owner.identity)
            self.strategy = parse_strategy_definition(self.record.definition_json)
            if self.strategy.required_timeframes != ('1h',):
                raise AssertionError('Draft requires existing registered robust 1h strategy, not another definition')
            bars = []
            for index, value in enumerate(('59970', '59980', '59990', '60000')):
                close_at = self.now - timedelta(hours=3-index)
                price = Decimal(value)
                bars.append(Candle('contracts-v0.1', self.record.symbol, '1h',
                    close_at-timedelta(hours=1), close_at, price, price+1, price-1,
                    price, Decimal('1'), True, 'FIXTURE_H01_NO_PROVIDER',
                    received_at=close_at, source_record_id='h01-candle-'+str(index)))
            self.bundle = build_asof_bundle({'1h': tuple(bars)}, self.now, self.now)
            self.admission = RuntimeAdmission(namespace='FIXTURE', registry_factory=owner.factory,
                current_preflight=owner.preflight, clock=lambda:owner.clock[0],
                maximum_observation_age_seconds=5)
            permit = self.admission.issue(owner.identity, expected_revision=owner.revision,
                permission='NEW_EXPOSURE', execution='FAKE_PROVIDER_VERIFICATION')
            self.current = self.admission.current_authority(permit, identity=owner.identity,
                permission='NEW_EXPOSURE', execution='FAKE_PROVIDER_VERIFICATION')
            self.selected = parse_product_risk_policy(json.loads(self.current.risk_policy_json), namespace='FIXTURE')
            if self.selected.policy_hash != self.current.permission.release.risk_policy_hash:
                raise AssertionError('Actual selected owner E5 policy binding required')

            # Explicit caller-owned FIXTURE vectors, matching actual empty native
            # prerequisites below. These values are never defaults in runner code.
            self.context = RiskContext(market_health_status='HEALTHY', market_data_fresh=True,
                account_state_status='KNOWN', account_state_known=True,
                position_state_status='FLAT', position_state_known=True,
                order_state_status='KNOWN', order_state_known=True,
                kill_switch_active=False, new_exposure_allowed=True, trades_today=0,
                open_position_count=0, same_symbol_position_open=False,
                consecutive_losses=0, drawdown=Decimal('0'), available_balance=Decimal('100'))
            self.signal = StrategyRuntime().evaluate(self.strategy, self.bundle, self.now)
            if self.signal['direction'] != 'LONG':
                raise AssertionError('Real registered E2 must produce LONG on the explicit rising candles')
            self.exit_request = build_exit_request(self.strategy, self.bundle)
            constraints = resolve_exit_constraints(self.exit_request)
            reference = Decimal(self.signal['reference_price'])
            quantity = Decimal('0.001')
            self.proposal = RiskProposal(quantity=quantity, notional=quantity*reference,
                margin=quantity*reference, leverage=Decimal('1'),
                estimated_max_loss=quantity*abs(reference-constraints.stop_level),
                estimated_cost=Decimal('0'),
                reward_amount=quantity*abs(constraints.target_level-reference),
                required_stop_level=constraints.stop_level, required_target_level=constraints.target_level)
            self.intent = build_trade_intent(self.signal, entry_profile_version='entry-v0.1',
                entry_order_type='MARKET', generated_at=self.now,
                strategy_stop_level=constraints.stop_level, strategy_target_level=constraints.target_level,
                max_hold_seconds=constraints.max_hold_seconds)
            self.risk = evaluate_trade_intent(self.intent, self.context, self.proposal,
                self.selected.risk_policy, decided_at=self.now)
            if self.risk['decision'] != 'APPROVE':
                raise AssertionError('Actual E5 rejected proposed test vector: '+repr(self.risk['reason_codes']))
            self.plan = build_approved_trade_plan(self.intent, self.risk, self.selected.risk_policy, created_at=self.now)
            self.capabilities = OKXProductCapabilityOwner()
            self.account = OKXAccountConfigSnapshot('2', 'net_mode', '123', '123')
            self.metadata = replace(metadata_fixtures._metadata(self.now), ct_val=Decimal('0.0001'))
            self.proof = self.capabilities.issue('ENTRY', self.account, self.metadata,
                observed_at=self.now, now=self.now)
            self.prerequisites = OKXPrerequisiteSnapshot(self.account, (), ())
            self.prerequisites_proof = self.capabilities.observe_entry_prerequisites(
                self.prerequisites, observed_at=self.now, now=self.now)
            # Independent normal E4 composition only computes expected wire identity;
            # it is never passed as the runner input or persisted as accepted output.
            expected = OKXProductTranslator(self.capabilities).prepare_entry(plan=self.plan,
                metadata=self.metadata, prerequisites=self.prerequisites, proof=self.proof,
                prerequisites_proof=self.prerequisites_proof, now=self.now)
            self.request = expected.canonical_request
            ack = dict(code='0', data=[dict(ordId='1234',
                clOrdId=expected.materialization.provider_cl_ord_id, sCode='0')])
            order = dict(expected.materialization.body)
            order.update(instType='SWAP', ordId='1234', state='live', accFillSz='0', avgPx='0', reduceOnly=False)
            self.order_response=dict(code='0',data=[order]);self.fill_response=dict(code='0',data=[])
            self.provider = FakeProductProvider([ack,self.order_response,self.fill_response])
            self.dispatch = open_product_dispatch_journal(owner.root/'h01-dispatch.sqlite')
            self.canonical = open_paper_runtime_journal(owner.root/'h01-canonical.sqlite')
            self.service = TradingService(admission=self.admission,
                translator=OKXProductTranslator(self.capabilities), dispatch=self.dispatch,
                canonical=self.canonical, provider=self.provider, identity=owner.identity,
                run_id='h01-real-e2-entry', clock=lambda:owner.clock[0])
            self.service.bind_process(expected_revision=owner.revision, expected_generation=0)
            self.arguments = dict(selected_risk=self.selected, risk_context=self.context,
                risk_proposal=self.proposal, metadata=self.metadata, prerequisites=self.prerequisites,
                capability_proof=self.proof, prerequisites_proof=self.prerequisites_proof,
                expected_revision=owner.revision)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.canonical is not None:
            self.canonical.close()
        if self.dispatch is not None:
            self.dispatch.close()
        self.authority.doCleanups()
