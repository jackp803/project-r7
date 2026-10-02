import importlib
from decimal import Decimal,localcontext
import unittest

def fixture_policy(algorithm='TRADE_PERMUTATION'):
    return dict(schema_version='r7-monte-carlo-policy-v0.2',algorithm=algorithm,
                algorithm_version='r7-mc-v1',rng_algorithm='SHA256_COUNTER_REJECTION_V1',resample_count=20,
                minimum_samples=5,minimum_effective_blocks=2,block_length=2,
                sample_source='CLOSED_DEVELOPMENT_TRADE_NET_PNL_USDT',initial_equity='1000',
                drawdown_unit='USDT_AMOUNT',max_path_observations=10000,
                dependence_model='ORDER_SENSITIVITY' if algorithm=='TRADE_PERMUTATION' else 'OVERLAPPING_FIXED_BLOCKS')

class MonteCarloTests(unittest.TestCase):
    def api(self):
        try: return importlib.import_module('validation.robustness.monte_carlo')
        except ModuleNotFoundError: self.fail('Missing E3 versioned Monte Carlo owner')

    def test_seeded_permutation_reproduces_pinned_order_but_never_infers_expectancy(self):
        api=self.api(); sample=['2','-3','1','4','-2','3']; policy=fixture_policy()
        one=api.evaluate_monte_carlo(sample,policy,seed=42).as_dict()
        two=api.evaluate_monte_carlo(sample,policy,seed=42).as_dict()
        self.assertEqual(one,two)
        self.assertEqual('PASS',one['status'])
        self.assertEqual([4,3,2,1,5,0],one['samples'][0]['source_indices'])
        self.assertEqual('DRAWDOWN_ORDER_SENSITIVITY_ONLY',one['interpretation'])
        self.assertIsNone(one['expectancy_quantiles'])
        self.assertEqual({'5'},{item['net_pnl'] for item in one['samples']})
        self.assertEqual(20,one['resample_count'])
        self.assertEqual('SHA256_COUNTER_REJECTION_V1',one['rng_algorithm'])
        changed=api.evaluate_monte_carlo(sample,policy,seed=43).as_dict()
        self.assertNotEqual(one['samples'],changed['samples'])

    def test_moving_blocks_preserve_local_order_and_record_conditional_sensitivity(self):
        api=self.api(); policy=fixture_policy('MOVING_BLOCK_BOOTSTRAP'); sample=['2','-3','1','4','-2','3']
        result=api.evaluate_monte_carlo(sample,policy,seed=42).as_dict()
        self.assertEqual('PASS',result['status'])
        self.assertEqual('CONDITIONAL_BLOCK_RESAMPLING_SENSITIVITY',result['interpretation'])
        self.assertIsNotNone(result['expectancy_quantiles'])
        for item in result['samples']:
            self.assertEqual(6,len(item['source_indices']))
            for i in range(0,6,2): self.assertEqual(item['source_indices'][i]+1,item['source_indices'][i+1])
        self.assertIn('Dependence beyond selected block length is not modeled',result['limitations'])

    def test_empty_small_and_too_few_blocks_are_insufficient_not_zero_risk_pass(self):
        api=self.api()
        for sample,policy in (([],fixture_policy()),(['1','2'],fixture_policy()),
                              (['1']*6,dict(fixture_policy('MOVING_BLOCK_BOOTSTRAP'),block_length=4))):
            with self.subTest(size=len(sample)):
                result=api.evaluate_monte_carlo(sample,policy,seed=42).as_dict()
                self.assertEqual('BLOCKED',result['status'])
                self.assertIn('INSUFFICIENT_EVIDENCE',result['reason_codes'])
                self.assertEqual([],result['samples'])
                self.assertIsNone(result['drawdown_quantiles'])

    def test_fraction_drawdown_has_explicit_equity_denominator_and_nearest_rank_quantiles(self):
        api=self.api(); policy=fixture_policy(); policy.update(initial_equity='100',drawdown_unit='FRACTION_OF_INITIAL_EQUITY',resample_count=1)
        result=api.evaluate_monte_carlo(['2','-3','1','4','-2','3'],policy,seed=42).as_dict()
        # Pinned order -2,+4,+1,-3,+3,+2 gives peak-to-trough3 USDT /100.
        self.assertEqual('0.03',result['samples'][0]['max_drawdown'])
        self.assertEqual({'0.05':'0.03','0.50':'0.03','0.95':'0.03'},result['drawdown_quantiles'])
        self.assertEqual('EMPIRICAL_NEAREST_RANK_V1',result['quantile_method'])
        self.assertEqual('100',result['initial_equity'])

    def test_fixed_decimal_profile_is_independent_of_ambient_context(self):
        api=self.api(); policy=fixture_policy('MOVING_BLOCK_BOOTSTRAP')
        sample=['0.123456789123456789','-0.333333333333333333','1.1','2.22','-3.333','4.4444']
        expected=api.evaluate_monte_carlo(sample,policy,seed=99).as_dict()
        with localcontext() as context:
            context.prec=5
            self.assertEqual(expected,api.evaluate_monte_carlo(sample,policy,seed=99).as_dict())
        sparse_policy=dict(policy,resample_count=7)
        sparse=api.evaluate_monte_carlo(['1','2'],sparse_policy,seed=99).as_dict()
        with localcontext() as context:
            context.prec=5
            self.assertEqual(sparse,api.evaluate_monte_carlo(['1','2'],sparse_policy,seed=99).as_dict())

    def test_unknown_float_seed_units_and_computation_budget_rejected(self):
        api=self.api(); sample=['1','-1','2','-2','3']
        for change in ({'decision':'PASS'},{'rng_algorithm':'host-random'},{'drawdown_unit':'PERCENT'},
                       {'max_path_observations':1},{'resample_count':10001},{'initial_equity':'NaN'}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                api.evaluate_monte_carlo(sample,dict(fixture_policy(),**change),seed=42)
        for seed in (True,-1,1.2):
            with self.subTest(seed=seed),self.assertRaises(ValueError): api.evaluate_monte_carlo(sample,fixture_policy(),seed=seed)
        with self.assertRaises(ValueError): api.evaluate_monte_carlo([1.0]*5,fixture_policy(),seed=42)
    def test_decimal_arithmetic_overflow_is_typed_incomplete_evidence(self):
        api=self.api()
        from decimal import DecimalException
        try:
            result=api.evaluate_monte_carlo(['9e999999']*5,fixture_policy(),seed=42).as_dict()
        except DecimalException:
            self.fail('Unstructured Decimal exception escaped research assessment')
        self.assertEqual('BLOCKED',result['status']); self.assertIn('ARITHMETIC_PROFILE_EXCEEDED',result['reason_codes'])
        self.assertEqual([],result['samples']); self.assertIsNone(result['drawdown_quantiles'])
