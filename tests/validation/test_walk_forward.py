import importlib
from datetime import timedelta
from tempfile import TemporaryDirectory
import unittest
from tests.validation.robustness_fixtures import inputs,subject,research_policy,robustness_policy
from tests.application.dataset_fixtures import START,z

class WalkForwardTests(unittest.TestCase):
    def test_walk_forward_entry_bounds_use_maximum_horizon_and_exact_embargo(self):
        import json
        from application.datasets.split_plan import resolve_split
        for hold,label in ((7200,3600),(3600,7200)):
            with self.subTest(hold=hold,label=label),TemporaryDirectory() as root:
                api=self.api()
                data,original,cost=inputs(root)
                split_policy=json.loads(original.canonical_policy_json)
                split_policy.update(max_holding_seconds=hold,label_horizon_seconds=label)
                split=resolve_split(data,split_policy)
                binding=api.DevelopmentBinding.from_dataset(data,split,cost)
                policy=robustness_policy(split,cost)
                for raw,clocks in zip(policy['walk_forward_windows'],((8,12,6,9,10),(12,16,10,13,14))):
                    window=binding.window(raw['evaluation'],embargo=True)
                    self.assertEqual((window.start,window.end,window.warmup_start,window.entry_start,window.entry_end),
                        tuple(START+timedelta(hours=n) for n in clocks))
                result=api.evaluate_robustness(subject(),binding,policy,
                    research_policy=research_policy(split,cost),seed=42).as_dict()['walk_forward']
                self.assertEqual(len(result['windows']),2)
                for window,(start,end) in zip(result['windows'],((9,10),(13,14))):
                    self.assertEqual(window['purge_seconds'],7200)
                    self.assertEqual(window['embargo_seconds'],3600)
                    self.assertEqual(window['evaluation_entry_start'],z(START+timedelta(hours=start)))
                    self.assertEqual(window['evaluation_entry_end'],z(START+timedelta(hours=end)))
                    for trade in window['evaluation']['trades']:
                        self.assertGreaterEqual(trade['opened_at'],window['evaluation_entry_start'])
                        self.assertLess(trade['opened_at'],window['evaluation_entry_end'])
                        self.assertLessEqual(trade['closed_at'],window['evaluation_end'])

    def api(self):
        try: return importlib.import_module('validation.robustness.evaluator')
        except ModuleNotFoundError: self.fail('Missing purged actual E3 walk-forward owner')
    def evaluate(self,root,change=None,mutate=None):
        api=self.api(); data,split,cost=inputs(root,mutate); policy=robustness_policy(split,cost)
        if change: change(policy)
        return api.evaluate_robustness(subject(),api.DevelopmentBinding.from_dataset(data,split,cost),policy,
                  research_policy=research_policy(split,cost),seed=42).as_dict()['walk_forward']
    def test_actual_training_selection_and_each_disjoint_scored_interval_once(self):
        with TemporaryDirectory() as root:
            result=self.evaluate(root)
            self.assertEqual('PASS',result['status']); self.assertEqual(2,len(result['windows']))
            ids=[]
            for window in result['windows']:
                self.assertEqual(4,len(window['training_variants']))
                self.assertEqual('FEATURE_ONLY',window['warmup'])
                self.assertEqual('PURGED',window['boundary_overlap'])
                self.assertGreater(window['purge_seconds'],0); self.assertGreater(window['embargo_seconds'],0)
                for trade in window['evaluation']['trades']:
                    self.assertGreaterEqual(trade['opened_at'],window['evaluation_entry_start'])
                    self.assertLess(trade['opened_at'],window['evaluation_entry_end'])
                    self.assertLessEqual(trade['closed_at'],window['evaluation_end'])
                    ids.append(trade['trade_id'])
            self.assertEqual(len(ids),len(set(ids)))
            self.assertEqual(len(ids),result['aggregate']['total_trades'])
    def test_overlap_misalignment_and_sealed_access_rejected(self):
        changes=(lambda p:p['walk_forward_windows'][1]['evaluation'].update(start=z(START+timedelta(hours=10))),
                 lambda p:p['walk_forward_windows'][0]['evaluation'].update(start=z(START+timedelta(hours=8,minutes=1))),
                 lambda p:p['walk_forward_windows'][1]['evaluation'].update(end=z(START+timedelta(hours=33))))
        for change in changes:
            with self.subTest(change=change),TemporaryDirectory() as root:
                with self.assertRaises(ValueError): self.evaluate(root,change)
    def test_later_evaluation_values_cannot_change_earlier_training_choice(self):
        with TemporaryDirectory() as first,TemporaryDirectory() as second:
            original=self.evaluate(first)
            def mutate(rows):
                for row in rows[12:]: row.update(open='1000',high='1002',low='999',close='1001')
            changed=self.evaluate(second,mutate=mutate)
            self.assertEqual(original['windows'][0]['selected_variant_hash'],changed['windows'][0]['selected_variant_hash'])
            self.assertEqual(original['windows'][0]['evaluation']['net_pnl'],changed['windows'][0]['evaluation']['net_pnl'])
            before=[v.get('backtest',{}).get('net_pnl') for v in original['windows'][0]['training_variants']]
            after=[v.get('backtest',{}).get('net_pnl') for v in changed['windows'][0]['training_variants']]
            self.assertEqual(before,after)
    def test_stitched_loss_streak_is_checked_even_when_each_window_meets_its_limit(self):
        api=self.api(); self.assertTrue(hasattr(api,'assess_walk_forward_aggregate'),'Missing actual aggregate policy gate')
        with TemporaryDirectory() as root:
            _,split,cost=inputs(root); p=research_policy(split,cost)
            p.update(min_net_pnl_usdt='-10',min_expectancy_usdt_per_trade='-10',max_consecutive_losses=1)
            policy=api.ResearchPolicy.parse(p)
            trade=dict(net_pnl='-1',gross_pnl='-1',total_fees='0',slippage_cost='0',funding_cost='0')
            one=api.assess_walk_forward_aggregate([trade],policy)
            self.assertEqual('PASS',one['assessment']['status'])
            stitched=api.assess_walk_forward_aggregate([trade,trade],policy)
            self.assertEqual(2,stitched['metrics']['max_consecutive_losses'])
            self.assertEqual('FAIL',stitched['assessment']['status'])
            self.assertIn('MAX_CONSECUTIVE_LOSSES_EXCEEDED',stitched['assessment']['reason_codes'])
