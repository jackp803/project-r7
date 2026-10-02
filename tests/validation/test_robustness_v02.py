import copy
import importlib
from decimal import localcontext
from tempfile import TemporaryDirectory
import unittest
from tests.validation.robustness_fixtures import inputs,subject,research_policy,robustness_policy

class RobustnessTests(unittest.TestCase):
    def test_public_versioned_policy_schemas_are_strict_and_match_runtime_profiles(self):
        import json,jsonschema
        from pathlib import Path
        from tests.validation.test_monte_carlo import fixture_policy
        contracts=Path(__file__).resolve().parents[2]/'contracts'
        with TemporaryDirectory() as root:
            data,split,cost=inputs(root)
            for name,value in (('research_policy_v0_2',research_policy(split,cost)),('robustness_policy_v0_2',robustness_policy(split,cost)),
                               ('monte_carlo_policy_v0_2',fixture_policy())):
                path=contracts/(name+'.schema.json'); self.assertTrue(path.is_file(),'Missing strict schema '+name)
                schema=json.loads(path.read_text()); jsonschema.Draft202012Validator.check_schema(schema)
                validator=jsonschema.Draft202012Validator(schema); validator.validate(value)
                forged=copy.deepcopy(value); forged['decision']='PASS'; self.assertTrue(list(validator.iter_errors(forged)))
                if 'drawdown_unit' in value:
                    forged=copy.deepcopy(value); forged['drawdown_unit']='PERCENT'; self.assertTrue(list(validator.iter_errors(forged)))
    def api(self):
        try: return importlib.import_module('validation.robustness.evaluator')
        except ModuleNotFoundError: self.fail('Missing actual E3 robustness replay owner')
    def execute(self,root,*,change=None,mutate=None):
        api=self.api(); data,split,cost=inputs(root,mutate); policy=robustness_policy(split,cost)
        if change: change(policy)
        binding=api.DevelopmentBinding.from_dataset(data,split,cost)
        return api.evaluate_robustness(subject(),binding,policy,research_policy=research_policy(split,cost),seed=42).as_dict()
    def test_actual_e2_e3_replays_preserve_every_invalid_and_insufficient_variant(self):
        with TemporaryDirectory() as root:
            result=self.execute(root)
            self.assertEqual('PASS',result['status'])
            variants=result['neighborhood']['variants']
            self.assertEqual(4,len(variants)); self.assertEqual(4,len({v['variant_hash'] for v in variants}))
            self.assertEqual(['BLOCKED','PASS','PASS','INVALID'],[v['status'] for v in variants])
            self.assertIn('INVALID_WINDOW',variants[-1]['reason_codes'])
            self.assertEqual('0.5',result['neighborhood']['pass_fraction'])
            self.assertTrue(all(v['backtest']['reproducibility']['runtime_invocations']>0 for v in variants[:-1]))
            self.assertTrue(result['raw_result_hashes'])
            self.assertEqual(2,len(result['monte_carlo']))
            self.assertEqual('E2',result['development']['backtest']['reproducibility']['runtime_provider'])
    def test_adaptive_binding_has_no_sealed_rows_or_funding_events(self):
        api=self.api()
        with TemporaryDirectory() as root:
            data,split,cost=inputs(root); bound=api.DevelopmentBinding.from_dataset(data,split,cost)
            self.assertTrue(all(row.close_time<=split.development.end for rows in bound.candles_by_timeframe.values() for row in rows))
            self.assertTrue(all(event<split.development.end for event,_ in bound.funding_model.events))
            self.assertFalse(hasattr(bound,'sealed_oos')); self.assertFalse(hasattr(bound,'dataset'))
            with self.assertRaises(TypeError): bound.candles_by_timeframe['1h']=()
    def test_stress_replays_keep_unfavorable_cost_outcomes_and_fail_selected_criterion(self):
        def adverse(p): p['stress_scenarios'][0]['fee_add_bps']='1000'
        with TemporaryDirectory() as root:
            result=self.execute(root,change=adverse)
            self.assertEqual('FAIL',result['status'])
            self.assertIn('STRESS_TOLERANCE_NOT_MET',result['reason_codes'])
            stressed=result['stress']['scenarios'][0]
            self.assertLess(float(stressed['backtest']['net_pnl']),0)
            self.assertGreater(float(stressed['backtest']['total_fees']),0)
            self.assertIn('Adverse funding always charges absolute recorded event cost',stressed['assumptions'])
    def test_no_selected_policy_and_too_few_samples_are_blocked_not_quantitative_fail(self):
        api=self.api()
        with TemporaryDirectory() as root:
            data,split,cost=inputs(root); bound=api.DevelopmentBinding.from_dataset(data,split,cost)
            result=api.evaluate_robustness(subject(),bound,robustness_policy(split,cost),research_policy=None,seed=42).as_dict()
            self.assertEqual('BLOCKED',result['status']); self.assertIn('MISSING_RESEARCH_POLICY',result['reason_codes'])
            rp=research_policy(split,cost); rp['minimum_closed_trades']['development']=100
            result=api.evaluate_robustness(subject(),bound,robustness_policy(split,cost),research_policy=rp,seed=42).as_dict()
            self.assertEqual('BLOCKED',result['status']); self.assertIn('INSUFFICIENT_EVIDENCE',result['reason_codes'])
    def test_unknown_and_over_budget_profiles_do_not_begin_replay(self):
        api=self.api()
        for change in (lambda p:p.update(decision='PASS'),lambda p:p.update(maximum_trials=3),
                       lambda p:p.update(maximum_replays=1),lambda p:p.update(maximum_evaluations=1),
                       lambda p:p['neighborhood'][0].update(parameter='unused_parameter')):
            with self.subTest(change=change),TemporaryDirectory() as root:
                with self.assertRaises(ValueError): self.execute(root,change=change)
    def test_declared_budget_is_admitted_before_any_e2_runtime_execution(self):
        from unittest.mock import patch
        api=self.api()
        with TemporaryDirectory() as root:
            data,split,cost=inputs(root); p=robustness_policy(split,cost); p['maximum_replays']=1
            with patch.object(api,'project_e2_runtime_binding',wraps=api.project_e2_runtime_binding) as executed:
                with self.assertRaises(ValueError): api.evaluate_robustness(subject(),api.DevelopmentBinding.from_dataset(data,split,cost),p,
                                         research_policy=research_policy(split,cost),seed=42)
                self.assertEqual(0,executed.call_count)
    def test_legacy_validation_policy_receives_drawdown_amount_with_explicit_equity(self):
        api=self.api()
        with TemporaryDirectory() as root:
            data,split,cost=inputs(root); policy=research_policy(split,cost)
            policy.update(drawdown_unit='FRACTION_OF_INITIAL_EQUITY',drawdown_limit='0.02',initial_equity_usdt='1234')
            actual=api.ResearchPolicy.parse(policy)
            self.assertEqual('24.68',str(actual.validation_policy('development').max_drawdown))
            self.assertEqual('0.02',actual.as_dict()['drawdown_limit'])
            policy['drawdown_unit']='PERCENT'
            with self.assertRaises(ValueError): api.ResearchPolicy.parse(policy)
    def test_frozen_outputs_and_decimal_profile_cannot_be_changed_by_caller(self):
        api=self.api()
        with TemporaryDirectory() as root:
            data,split,cost=inputs(root); bound=api.DevelopmentBinding.from_dataset(data,split,cost)
            p=robustness_policy(split,cost); rp=research_policy(split,cost)
            assessment=api.evaluate_robustness(subject(),bound,p,research_policy=rp,seed=42)
            expected=assessment.as_dict(); p['neighborhood'][0]['values']=[3]; changed=assessment.as_dict(); changed['status']='FAIL'
            self.assertEqual(expected,assessment.as_dict())
            with localcontext() as context:
                context.prec=5
                repeated=api.evaluate_robustness(subject(),bound,robustness_policy(split,cost),research_policy=rp,seed=42).as_dict()
            self.assertEqual(expected,repeated)
