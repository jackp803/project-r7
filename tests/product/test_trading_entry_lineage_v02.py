"""Inject corruption before the actual immutable owner writer, without DB edits."""
import json
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from application.trading.orchestrator import TradingOrchestrator
from storage.product_dispatch import ProductDispatchError, _json
from tests.product.h01_entry_fixture import H01EntryFixture


class TradingEntryLineageV02Tests(unittest.TestCase):
    def test_original_e2_signal_exit_and_intent_links_are_required_before_stage(self):
        mutations = (
            ('trade_intent', 'generated_at', 'future'),
            ('signal', 'strategy_content_hash', 'sha256:'+'f'*64),
            ('signal', 'evaluated_at', 'future'),
            ('trade_intent', 'market_boundary_ref', 'different-boundary'),
            ('exit_request', 'market_boundary_ref', 'different-boundary'),
            ('exit_request', 'direction', 'SHORT'),
        )
        for section, key, replacement in mutations:
            with self.subTest(section=section, key=key), H01EntryFixture() as f:
                real_stage = f.dispatch.stage_entry_decision
                def corrupt_before_actual_stage(run_id, identity, boundary, observation, **kwargs):
                    evidence = json.loads(observation.evidence_json)
                    evidence[section][key] = ((f.now+timedelta(seconds=1)).isoformat().replace('+00:00','Z')
                        if replacement == 'future' else replacement)
                    return real_stage(run_id, identity, boundary,
                        replace(observation, evidence_json=_json(evidence)), **kwargs)
                with patch.object(f.dispatch, 'stage_entry_decision', side_effect=corrupt_before_actual_stage):
                    with self.assertRaisesRegex(ProductDispatchError, 'ENTRY_EXACT_E2_'):
                        TradingOrchestrator(f.service).evaluate_entry(f.bundle, **f.arguments)
                self.assertEqual([], f.provider.calls)
                self.assertIsNone(f.dispatch.entry_decision(f.service.run_id,
                    f.authority.identity, f.bundle.boundary))
                recovered = f.canonical.recover(trade_plan_id=f.plan['trade_plan_id'])
                self.assertIsNone(recovered.risk_decision)
                self.assertIsNone(recovered.approved_trade_plan)
