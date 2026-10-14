"""Sealed finite synthetic inputs only; never stored results or qualification."""
from datetime import datetime,timedelta,timezone
import importlib,importlib.util,json,unittest
from types import SimpleNamespace

from application.config import load_config
from application.fixtures.recipe import prepare_fixture,SUBMISSION
from application.local_owners import LocalOwners
from application.platform.scope_lock import ProcessScopeLock,ScopeBusy,operational_lock_root
from tests.application import test_fixture_recipe_flow as recipe
from tests.application import test_research_setup_flow as normal


class FixturePaperCaseRecipeTests(unittest.TestCase):
    setUp=recipe.FixtureRecipeFlowTests.setUp
    call=recipe.FixtureRecipeFlowTests.call
    initialize=recipe.FixtureRecipeFlowTests.initialize
    configure=recipe.FixtureRecipeFlowTests.configure

    def cases(self):
        self.assertIsNotNone(importlib.util.find_spec('application.fixtures.faults'),'Finite sealed recovery cases missing')
        return importlib.import_module('application.fixtures.faults')

    def prepare(self,case):
        config=self.initialize();result=prepare_fixture(self.config_path,'positive',paper_case=case)
        self.profile=self.data/result['selection_profile_ref']
        return config,result

    def test_partial_case_seals_only_declarative_inputs_and_existing_fraction(self):
        config,result=self.prepare('partial-fill-hold');module=self.cases()
        package=self.cloud/'inbox/strategies'/SUBMISSION
        document=json.loads((self.data/module.REFERENCE).read_bytes())
        self.assertEqual(json.loads((package/'research_notes.md').read_bytes()),document)
        manifest=json.loads((package/'manifest.json').read_bytes())
        self.assertEqual(manifest['intent_class'],'EVERGREEN_STRATEGY')
        self.assertEqual(json.loads((self.data/'fixture-inputs/simulation.json').read_bytes())['initial_fill_fraction'],'0.5')
        self.assertEqual(json.loads((self.data/'fixture-inputs/paper-selection.json').read_bytes())['paper_policy_ref'],module.policy_ref(document))
        self.assertEqual(result['execution_evidence'],'NOT_RUN');self.assertFalse(config.database_path.exists())

    def test_default_normal_keeps_legacy_notes_policy_and_market_behavior(self):
        _,_=self.prepare('normal');module=self.cases()
        package=self.cloud/'inbox/strategies'/SUBMISSION
        self.assertFalse((package/'research_notes.md').exists());self.assertFalse((self.data/module.REFERENCE).exists())
        self.assertEqual(json.loads((self.data/'fixture-inputs/simulation.json').read_bytes())['initial_fill_fraction'],'1')
        self.assertEqual(json.loads((self.data/'fixture-inputs/paper-selection.json').read_bytes())['paper_policy_ref'],'r7-synthetic-paper-policy')

    def test_unknown_case_and_mixed_temporal_case_deny_before_creating_inputs(self):
        self.initialize()
        for kwargs in ({'paper_case':'arbitrary-price-or-code'},
                {'paper_case':'fill-at-target'},
                {'paper_case':'hold-for-recovery','temporal_case':'paper-expire-after-protection'}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):prepare_fixture(self.config_path,'positive',**kwargs)
        self.assertFalse(self.data.exists());self.assertFalse(self.cloud.exists())

    def test_ordinary_namespace_cannot_create_case_inputs(self):
        normal.ResearchSetupFlowTests.initialize(self)
        with self.assertRaises(ValueError):prepare_fixture(self.config_path,'positive',paper_case='hold-for-recovery')
        self.assertFalse(self.data.exists());self.assertFalse(self.cloud.exists())

    def test_running_owner_scope_denies_case_generation_before_inputs(self):
        config=self.initialize()
        with ProcessScopeLock('runtime:'+config.product_instance_id,lock_root=operational_lock_root(config)):
            with self.assertRaises(ScopeBusy):prepare_fixture(self.config_path,'positive',paper_case='hold-for-recovery')
        self.assertFalse((self.data/'fixture-inputs').exists());self.assertFalse(self.cloud.exists())

    def test_schema_rejects_terminal_flags_price_time_code_and_unknown_case(self):
        module=self.cases();document=module.generate('hold-for-recovery')
        for changes in ({'passed':True},{'price':'60001'},{'terminal_state':'CLOSED'},
                {'clock':'arbitrary'},{'code':'anything'},{'case':'not-registered'},{'submission_id':'other'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):module.validate({**document,**changes})

    def test_reader_requires_actual_sealed_case_and_matching_auxiliary_bytes(self):
        config,_=self.prepare('hold-for-recovery');self.configure()
        owners=LocalOwners(config,namespace='FIXTURE')
        with owners.inbox_factory() as inbox:self.assertEqual(inbox.scan_once(datetime.now(timezone.utc)).accepted,1)
        _,package=owners.resolver.package(SUBMISSION);module=self.cases()
        self.assertEqual(module.read_case(config,package)['case'],'hold-for-recovery')
        path=self.data/module.REFERENCE;original=path.read_bytes()
        path.write_bytes(original+b' ')
        with self.assertRaises(ValueError):module.read_case(config,package)
        path.write_bytes(original);path.unlink()
        with self.assertRaises(ValueError):module.read_case(config,package)

    def test_named_market_hold_target_partial_and_single_missing_stale_duplicate_phase(self):
        module=self.cases();from application.fixtures.market import fixture_market_event
        first=datetime(2026,10,14,10,tzinfo=timezone.utc)
        empty=dict(position=None,candles={},entry_request=None,exit_anchor=None,last_market=None)
        hold=module.generate('hold-for-recovery')
        self.assertEqual(fixture_market_event(empty,first,paper_case=hold).snapshot.last_price,60000)
        protected=dict(empty,position={'lifecycle_state':'OPEN_PROTECTED'},candles={'1h':[]},
            exit_anchor={'payload':{'first_fill_at':first.isoformat().replace('+00:00','Z')}})
        initial=fixture_market_event(protected,first,paper_case=hold)
        # Actual durable last snapshot is the source of the duplicate input.
        protected['last_market']=initial.snapshot.to_interchange_dict()
        self.assertEqual(fixture_market_event(protected,first+timedelta(seconds=29),paper_case=hold).snapshot.last_price,60000)
        self.assertEqual(fixture_market_event(protected,first+timedelta(seconds=30),paper_case=hold).snapshot.last_price,60020)
        self.assertIsNone(fixture_market_event(protected,first+timedelta(seconds=1),paper_case=module.generate('missing-market-hold')))
        self.assertIsNone(fixture_market_event(protected,first+timedelta(seconds=7),paper_case=module.generate('missing-market-hold')))
        from application.paper.engine import PaperEngine
        owner=SimpleNamespace(config={'market_max_age_seconds':5},strategy=SimpleNamespace(symbol=initial.snapshot.symbol))
        self.assertFalse(PaperEngine._fresh(owner,initial.snapshot,first+timedelta(seconds=7)))
        restored=fixture_market_event(protected,first+timedelta(seconds=8),paper_case=module.generate('missing-market-hold'))
        self.assertEqual(restored.snapshot.observed_at,first+timedelta(seconds=8))
        self.assertTrue(PaperEngine._fresh(owner,restored.snapshot,first+timedelta(seconds=8)))
        stale=fixture_market_event(protected,first+timedelta(seconds=1),paper_case=module.generate('stale-market-hold'))
        self.assertEqual(stale.snapshot.freshness_ms,10000)
        duplicate=fixture_market_event(protected,first+timedelta(seconds=1),paper_case=module.generate('duplicate-market-hold'))
        self.assertEqual(duplicate.snapshot,initial.snapshot)
        rejected=fixture_market_event(dict(empty,entry_request={'actual-owner-request':'present'}),first,paper_case=module.generate('protection-rejected-hold'))
        self.assertEqual(rejected.snapshot.last_price,60000)

    def test_case_policy_reference_and_partial_fraction_are_exact(self):
        module=self.cases();document=module.generate('partial-fill-hold')
        selected=dict(paper_policy_ref=module.policy_ref(document),simulation_policy={'initial_fill_fraction':'0.5'})
        module.require_selection(document,selected)
        for changed in ({**selected,'paper_policy_ref':'unrelated-policy'},
                {**selected,'simulation_policy':{'initial_fill_fraction':'1'}}):
            with self.assertRaises(ValueError):module.require_selection(document,changed)


if __name__=='__main__':unittest.main()
