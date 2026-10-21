"""Version pairing for ordinary settled-public-rate Paper; no native credit."""
import unittest

from application.paper.policy import parse_simulation_policy
from tests.product.test_paper_runtime_v02 import simulation_fixture


def recorded_policy():
    value=simulation_fixture()
    value.update(schema_version='r7-paper-simulation-policy-v0.5',namespace='LOCAL_RESEARCH',
        mode='REAL_TIME',funding_model='OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1')
    return value


class RecordedPaperPolicyTests(unittest.TestCase):
    def test_new_ordinary_profile_explicitly_binds_recorded_model(self):
        value=recorded_policy()
        self.assertEqual(parse_simulation_policy(value,namespace='LOCAL_RESEARCH').as_dict(),value)

    def test_wrong_missing_zero_or_fixture_pairing_is_refused(self):
        for changes in ({'funding_model':'EXPLICIT_REGISTERED_PAPER_ZERO'},
                {'funding_model':None},{'schema_version':'r7-paper-simulation-policy-v0.2'},
                {'namespace':'FIXTURE','mode':'ACCELERATED_FIXTURE'}):
            value=recorded_policy();value.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                parse_simulation_policy(value,namespace=value['namespace'])
        value=recorded_policy();value.pop('funding_model')
        with self.assertRaises(ValueError):parse_simulation_policy(value,namespace='LOCAL_RESEARCH')

    def test_existing_ordinary_and_fixture_zero_policy_bytes_stay_supported(self):
        for namespace,mode in (('FIXTURE','ACCELERATED_FIXTURE'),('LOCAL_RESEARCH','REAL_TIME')):
            value=simulation_fixture();value.update(namespace=namespace,mode=mode)
            self.assertEqual(parse_simulation_policy(value,namespace=namespace).as_dict(),value)


if __name__=='__main__':unittest.main()
