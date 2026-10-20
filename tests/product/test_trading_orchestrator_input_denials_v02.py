"""H01 actual source/policy/clock fail-closed tests.

No substituted E2/risk results, provider response injection or SQL state writes.
"""
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from application.trading.orchestrator import TradingOrchestrator
from storage.product_dispatch import ProductDispatchError
from strategy import StrategyRuntime
from strategy.v02.temporal import build_asof_bundle
from tests.product import h01_entry_fixture as fixtures


def _flat_bundle(f):
    price=Decimal('60000')
    rows=tuple(replace(row,open=price,high=price+1,low=price-1,close=price)
               for row in f.bundle.candles_by_timeframe['1h'])
    return build_asof_bundle({'1h':rows},f.bundle.boundary,f.bundle.information_cutoff)


class TradingOrchestratorInputDenialsV02Tests(unittest.TestCase):
    def test_future_asof_historical_assumption_and_owner_policy_object_forgery_have_zero_effects(self):
        with fixtures.H01EntryFixture() as f:
            runner=TradingOrchestrator(f.service)
            rows=f.bundle.candles_by_timeframe
            future_boundary=build_asof_bundle(rows,f.now+timedelta(hours=1),f.now)
            future_cutoff=build_asof_bundle(rows,f.now,f.now+timedelta(seconds=1))
            historical=build_asof_bundle(rows,f.now,f.now,availability_model='historical_close_assumption')
            # Canonical JSON/hash remain exactly owner-selected; only the typed
            # risk object is forged. The real owner-parsed policy must win.
            forged=replace(f.selected,risk_policy=replace(f.selected.risk_policy,
                max_margin=f.selected.risk_policy.max_margin+Decimal('1')))
            self.assertEqual(f.selected.canonical_json,forged.canonical_json)
            self.assertEqual(f.selected.policy_hash,forged.policy_hash)
            self.assertNotEqual(f.selected.risk_policy,forged.risk_policy)
            cases=(('future-boundary',future_boundary,f.arguments,'ENTRY_OPERATIONAL_ASOF_CLOCK_REQUIRED'),
                   ('future-cutoff',future_cutoff,f.arguments,'ENTRY_OPERATIONAL_ASOF_CLOCK_REQUIRED'),
                   ('historical-assumption',historical,f.arguments,'ENTRY_OPERATIONAL_ASOF_CLOCK_REQUIRED'),
                   ('forged-typed-policy',f.bundle,dict(f.arguments,selected_risk=forged),'ENTRY_CALLER_POLICY_OWNER_MISMATCH'))
            for label,bundle,arguments,code in cases:
                with self.subTest(case=label):
                    with self.assertRaises(ProductDispatchError) as caught:
                        runner.evaluate_entry(bundle,**arguments)
                    self.assertEqual(code,caught.exception.code)
                    self.assertIsNone(f.dispatch.entry_decision(f.service.run_id,f.authority.identity,bundle.boundary))
                    self.assertEqual((),f.dispatch.pending_entry_publications(f.service.run_id))
                    self.assertEqual([],f.provider.calls)
                    self.assertEqual([],f.canonical._store._connection.execute(
                        'SELECT object_kind,canonical_id FROM paper_runtime_objects').fetchall())
                    dispatch=f.dispatch.recover(f.service.run_id)
                    self.assertEqual((),dispatch.prepared_operations)
                    self.assertEqual((),dispatch.ambiguous_operations)

    def test_same_no_trade_boundary_changed_explicit_context_denies_without_replacing_original_decision(self):
        with fixtures.H01EntryFixture() as f:
            bundle=_flat_bundle(f)
            actual_signal=StrategyRuntime().evaluate(f.strategy,bundle,bundle.boundary)
            self.assertEqual('NO_TRADE',actual_signal['direction'])
            self.assertEqual(['NO_RULE_MATCHED'],actual_signal['reason_codes'])
            runner=TradingOrchestrator(f.service)
            first=runner.evaluate_entry(bundle,**f.arguments)
            self.assertEqual('NO_TRADE',first.status)
            saved=f.dispatch.entry_decision(f.service.run_id,f.authority.identity,bundle.boundary)
            self.assertEqual(actual_signal,saved.signal)
            self.assertEqual([],saved.effects)
            changed=replace(f.context,available_balance=Decimal('99'))
            self.assertNotEqual(f.context,changed)
            with self.assertRaises(ProductDispatchError) as caught:
                runner.evaluate_entry(bundle,**dict(f.arguments,risk_context=changed))
            self.assertEqual('ENTRY_BOUNDARY_INPUT_CONFLICT',caught.exception.code)
            self.assertEqual(saved,f.dispatch.entry_decision(f.service.run_id,f.authority.identity,bundle.boundary))
            repeated=runner.evaluate_entry(bundle,**f.arguments)
            self.assertEqual(first,repeated)
            self.assertEqual(saved,f.dispatch.entry_decision(f.service.run_id,f.authority.identity,bundle.boundary))
            self.assertEqual((),f.dispatch.pending_entry_publications(f.service.run_id))
            self.assertEqual([],f.canonical._store._connection.execute(
                'SELECT object_kind,canonical_id FROM paper_runtime_objects').fetchall())
            self.assertEqual([],f.provider.calls)
            dispatch=f.dispatch.recover(f.service.run_id)
            self.assertEqual((),dispatch.prepared_operations)
            self.assertEqual((),dispatch.ambiguous_operations)
