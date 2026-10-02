import unittest

from application.paper.policy import parse_simulation_policy
from tests.product.test_paper_runtime_v02 import simulation_fixture


class PaperConfigurationTests(unittest.TestCase):
    def test_explicit_isolated_account_profile_is_required_instead_of_hidden_balance_scope(self):
        try: selected=parse_simulation_policy(simulation_fixture(),namespace='FIXTURE')
        except ValueError: self.fail('Explicit isolated per-strategy PAPER account profile missing')
        self.assertEqual(selected.as_dict()['account_scope'],'ISOLATED_PER_STRATEGY_RUN')
        for field in simulation_fixture():
            missing=simulation_fixture(); missing.pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):
                parse_simulation_policy(missing,namespace='FIXTURE')

    def test_malformed_financial_values_and_fixture_real_namespace_mix_are_rejected(self):
        for field,value in (('quantity','oops'),('fee_rate','NaN'),('leverage',True),
            ('initial_fill_fraction','2'),('quantity','0'),('namespace','LOCAL_RESEARCH'),
            ('mode','REAL_TIME'),('account_scope','SHARED_REAL_ACCOUNT'),('generation',True)):
            changed=simulation_fixture(); changed[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                parse_simulation_policy(changed,namespace='FIXTURE')


if __name__=='__main__': unittest.main()
