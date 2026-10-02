import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from brokers.paper import PaperBroker
from brokers.paper_state import encode_fact
from execution.gateway import ExecutionGateway
from market_data.candle import Candle
from risk.engine import RiskContext, RiskProposal, build_approved_trade_plan, evaluate_trade_intent
from risk.product_policy import parse_product_risk_policy
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from strategy import StrategyRuntime, build_trade_intent, parse_strategy_definition
from strategy.v02.temporal import build_asof_bundle
from strategy.v02.exits import build_exit_request
from position.exit_requests import resolve_exit_constraints
from tests.application.test_product_assessment_binding import risk_fixture
from tests.storage.test_paper_process_journal import NOW
from tests.strategy.v02_fixtures import definition_v02


class PaperEffectRecoveryTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper'), 'Paper orchestration package missing')
        self.assertIsNotNone(importlib.util.find_spec('application.paper.orchestrator'), 'durable Paper effect publisher missing')
        from application.paper.orchestrator import PaperCoordinator, PaperStep
        return PaperCoordinator, PaperStep

    def binding(self):
        return dict(namespace='FIXTURE', mode='ACCELERATED_FIXTURE', strategy_id='fixture-v02-trend',
            strategy_version='0.2.0', strategy_content_hash=definition_v02()['content_hash'],
            implementation_hash='sha256:'+'2'*64, config_hash='sha256:'+'3'*64,
            risk_policy_hash=parse_product_risk_policy(risk_fixture(), namespace='FIXTURE').policy_hash,
            paper_policy_hash='sha256:'+'5'*64)

    def producer(self, step_type):
        def produce(state, request, now):
            strategy = parse_strategy_definition(definition_v02())
            candles = tuple(Candle('contracts-v0.1', strategy.symbol, '4h',
                NOW-timedelta(hours=(2-index)*4), NOW-timedelta(hours=(1-index)*4),
                Decimal(price), Decimal(price)+1, Decimal(price)-1, Decimal(price), Decimal('1'),
                True, 'EXPLICIT_FIXTURE', received_at=NOW) for index, price in enumerate(('59000', '60000')))
            bundle = build_asof_bundle({'4h': candles}, NOW, NOW)
            signal = StrategyRuntime().evaluate(strategy, bundle, NOW)
            exits = build_exit_request(strategy, bundle)
            constraints = resolve_exit_constraints(exits)
            intent = build_trade_intent(signal, entry_profile_version='entry-v0.1', entry_order_type='MARKET',
                generated_at=now, strategy_stop_level=constraints.stop_level,
                strategy_target_level=constraints.target_level, max_hold_seconds=constraints.max_hold_seconds)
            policy = parse_product_risk_policy(risk_fixture(), namespace='FIXTURE').risk_policy
            context = RiskContext('HEALTHY', True, 'KNOWN', True, 'FLAT', True, 'KNOWN', True,
                                  False, True, 0, 0, False, 0, Decimal('0'), Decimal('1000'))
            proposal = RiskProposal(Decimal('.001'), Decimal('60'), Decimal('60'), Decimal('1'),
                Decimal('.01'), Decimal('0'), Decimal('.02'), constraints.stop_level, constraints.target_level)
            risk = evaluate_trade_intent(intent, context, proposal, policy, decided_at=now)
            self.assertEqual(risk['decision'], 'APPROVE')
            plan = build_approved_trade_plan(intent, risk, policy, created_at=now)
            broker = PaperBroker.from_state(state['broker'])
            order = ExecutionGateway().prepare_entry_order(plan, now=now)
            result = broker.submit_order(order)
            effects = [dict(kind=kind, payload=payload) for kind, payload in (
                ('RISK_DECISION', risk), ('APPROVED_TRADE_PLAN', plan),
                ('ORDER_REQUEST', encode_fact(order)), ('ORDER_RESULT', encode_fact(result)))]
            return step_type(dict(broker=broker.export_state(), runtime={'signal': signal, 'intent': intent,
                             'plan': plan, 'entry_request': encode_fact(order)}), effects, 'ACKNOWLEDGED', ())
        return produce

    def test_crash_between_canonical_objects_recovers_same_actual_owner_effect(self):
        coordinator_type, step_type = self.api()
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'paper.sqlite'
            with open_paper_process_journal(path) as process, open_paper_runtime_journal(path) as canonical:
                process.create_run('run', self.binding(), {'broker': PaperBroker().export_state(), 'runtime': {}}, now=NOW)
                generation = process.begin_process('run', 'one', expected_generation=0, now=NOW)
                coordinator = coordinator_type(process, canonical, 'run', generation,
                                               self.producer(step_type), clock=lambda:NOW)
                with patch.object(type(canonical), 'persist_approved_trade_plan', side_effect=RuntimeError('injected publication crash')):
                    with self.assertRaises(RuntimeError): coordinator.execute('entry-boundary', {'kind': 'ENTRY'})
                self.assertEqual(process.recover('run').revision, 1)
                original = process.operation('run', 'entry-boundary')
                self.assertEqual(original.status, 'APPLIED')
            with open_paper_process_journal(path) as process, open_paper_runtime_journal(path) as canonical:
                generation = process.begin_process('run', 'two', expected_generation=1, now=NOW+timedelta(seconds=10))
                def cannot_recompute(*_): raise AssertionError('Applied effects cannot run E2/E5/E4 again')
                coordinator = coordinator_type(process, canonical, 'run', generation,
                    cannot_recompute, clock=lambda:NOW+timedelta(seconds=10))
                coordinator.recover_pending()
                current = process.operation('run', 'entry-boundary')
                self.assertEqual(current.status, 'PUBLISHED')
                self.assertEqual(current.effect_hash, original.effect_hash)
                broker = PaperBroker.from_state(process.recover('run').state['broker'])
                request = process.recover('run').state['runtime']['entry_request']
                self.assertEqual(broker.query_order(request['client_order_id']).requested_quantity, Decimal('.001'))
                recovered = canonical.recover(trade_plan_id=process.recover('run').state['runtime']['plan']['trade_plan_id'])
                self.assertEqual(len(recovered.order_requests), 1)
                self.assertEqual(len(recovered.order_result_observations), 1)

    def test_duplicate_boundary_keeps_original_risk_ack_and_checkpoint(self):
        coordinator_type, step_type = self.api()
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'paper.sqlite'
            with open_paper_process_journal(path) as process, open_paper_runtime_journal(path) as canonical:
                process.create_run('run', self.binding(), {'broker': PaperBroker().export_state(), 'runtime': {}}, now=NOW)
                generation = process.begin_process('run', 'one', expected_generation=0, now=NOW)
                coordinator = coordinator_type(process, canonical, 'run', generation,
                                               self.producer(step_type), clock=lambda:NOW)
                first = coordinator.execute('entry-boundary', {'kind': 'ENTRY'})
                second = coordinator.execute('entry-boundary', {'kind': 'ENTRY'})
                self.assertEqual(first, second)
                self.assertEqual(process.recover('run').revision, 1)
                self.assertEqual(second.status, 'ACKNOWLEDGED')
