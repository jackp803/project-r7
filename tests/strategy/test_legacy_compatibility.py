import json
from pathlib import Path
import unittest

from strategy import StrategyRuntime, compute_content_hash, parse_strategy_definition


class LegacyCompatibilityTests(unittest.TestCase):
    def test_preserved_actual_signal_goldens_from_pre_v02_executable(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/legacy_runtime_golden.json').read_text(encoding='utf-8'))
        definition=fixture['definition']
        self.assertEqual(definition['content_hash'],compute_content_hash(definition))
        strategy=parse_strategy_definition(definition)
        for case in fixture['cases']:
            with self.subTest(case=case['case']):
                actual=StrategyRuntime().evaluate(strategy,case['candles'],case['boundary'])
                self.assertEqual(case['signal'],actual)

