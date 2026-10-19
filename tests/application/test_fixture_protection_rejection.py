"""Closed source input semantics; native E5 recovery is separately measured."""
import json,unittest
from application.fixtures.recipe import prepare_fixture
from application.paper.policy import parse_simulation_policy
from tests.application import test_fixture_recipe_flow as recipe


class FixtureProtectionRejectionTests(unittest.TestCase):
    setUp=recipe.FixtureRecipeFlowTests.setUp
    call=recipe.FixtureRecipeFlowTests.call
    initialize=recipe.FixtureRecipeFlowTests.initialize

    def policy(self):
        self.initialize();prepare_fixture(self.config_path,'positive',paper_case='protection-rejected-hold')
        return json.loads((self.data/'fixture-inputs/simulation.json').read_bytes())

    def test_sealed_case_uses_explicit_fixture_only_version_without_financial_change(self):
        value=self.policy();parsed=parse_simulation_policy(value,namespace='FIXTURE')
        self.assertEqual(parsed.as_dict(),value)
        self.assertEqual(value['schema_version'],'r7-paper-simulation-policy-v0.3')
        self.assertEqual(value['fixture_protection_submission'],'REJECT')
        from application.fixtures.recipe import _policies
        original=_policies('positive')['simulation']
        legacy={k:v for k,v in value.items() if k!='fixture_protection_submission'}
        legacy['schema_version']='r7-paper-simulation-policy-v0.2'
        self.assertEqual(legacy,original)
        self.assertFalse((self.data/'canonical.sqlite3').exists())

    def test_rejection_version_is_closed_and_cannot_select_ordinary_paper(self):
        value=self.policy()
        for changes in ({'namespace':'LOCAL_RESEARCH','mode':'REAL_TIME'},
                {'fixture_protection_submission':'PASS'},{'code':'arbitrary'},
                {'schema_version':'r7-paper-simulation-policy-v0.2'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                parse_simulation_policy({**value,**changes},namespace=changes.get('namespace','FIXTURE'))
        from application.fixtures.faults import generate,require_selection,policy_ref
        selected=dict(paper_policy_ref=policy_ref(generate('hold-for-recovery')),simulation_policy=value)
        with self.assertRaises(ValueError):require_selection(generate('hold-for-recovery'),selected)

    def observation_case(self,case,mode):
        self.initialize();prepare_fixture(self.config_path,'positive',paper_case=case)
        value=json.loads((self.data/'fixture-inputs/simulation.json').read_bytes())
        self.assertEqual(value['schema_version'],'r7-paper-simulation-policy-v0.4')
        self.assertEqual(value['fixture_protection_observation'],mode)
        self.assertEqual(parse_simulation_policy(value,namespace='FIXTURE').as_dict(),value)
        from application.fixtures.faults import generate,require_selection,policy_ref
        require_selection(generate(case),dict(paper_policy_ref=policy_ref(generate(case)),simulation_policy=value))
        for change in ({'namespace':'LOCAL_RESEARCH','mode':'REAL_TIME'},{'fixture_protection_observation':'PASS'},
                       {'fixture_protection_submission':'REJECT'},{'schema_version':'r7-paper-simulation-policy-v0.2'}):
            with self.subTest(change=change),self.assertRaises(ValueError):parse_simulation_policy(dict(value,**change),namespace=change.get('namespace','FIXTURE'))
        with self.assertRaises(ValueError):require_selection(generate('hold-for-recovery'),dict(paper_policy_ref=policy_ref(generate('hold-for-recovery')),simulation_policy=value))

    def test_sealed_missing_read_selection_is_fixture_only(self):self.observation_case('protection-query-missing-hold','MISSING')
    def test_sealed_stale_read_selection_is_fixture_only(self):self.observation_case('protection-query-stale-hold','STALE')
    def test_sealed_actual_stop_cancel_selection_is_fixture_only(self):self.observation_case('protection-lost-hold','CANCELED')


if __name__=='__main__':unittest.main()
