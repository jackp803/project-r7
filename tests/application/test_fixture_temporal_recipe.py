"""Closed synthetic input cases; no stored result or ordinary authority."""
from datetime import datetime,timedelta,timezone
import importlib,json,time,unittest
from unittest.mock import patch

from application.config import load_config
from application.fixtures.recipe import prepare_fixture,SUBMISSION
from application.local_owners import LocalOwners
from tests.application import test_fixture_recipe_flow as recipe
from tests.application import test_research_setup_flow as normal


class FixtureTemporalRecipeTests(unittest.TestCase):
    setUp=recipe.FixtureRecipeFlowTests.setUp
    call=recipe.FixtureRecipeFlowTests.call
    initialize=recipe.FixtureRecipeFlowTests.initialize
    configure=recipe.FixtureRecipeFlowTests.configure

    def prepare(self,case):
        config=self.initialize()
        result=prepare_fixture(self.config_path,'positive',temporal_case=case)
        self.profile=self.data/result['selection_profile_ref']
        return config,result

    def temporal(self):
        return importlib.import_module('application.fixtures.temporal')

    def test_named_cases_seal_original_tactical_validity_as_input_only(self):
        config,result=self.prepare('paper-expire-after-protection')
        self.assertEqual(result['temporal_case'],'paper-expire-after-protection')
        package=self.cloud/'inbox/strategies'/SUBMISSION
        manifest=json.loads((package/'manifest.json').read_bytes())
        document=json.loads((self.data/'fixture-inputs/temporal.json').read_bytes())
        self.assertEqual(json.loads((package/'research_notes.md').read_bytes()),document)
        self.assertEqual(document['validity'],manifest['validity'])
        self.assertEqual(manifest['intent_class'],'TACTICAL_STRATEGY')
        selected=json.loads((self.data/'fixture-inputs/paper-selection.json').read_bytes())
        self.assertEqual(selected['paper_policy_ref'],self.temporal().policy_ref(document))
        self.assertFalse(config.database_path.exists())
        self.assertEqual(result['execution_evidence'],'NOT_RUN')

    def test_unknown_case_is_denied_before_any_inputs(self):
        self.initialize()
        with self.assertRaises(ValueError):prepare_fixture(self.config_path,'positive',temporal_case='arbitrary-stage')
        self.assertFalse(self.data.exists())
        self.assertFalse(self.cloud.exists())

    def test_ordinary_namespace_cannot_receive_temporal_inputs(self):
        normal.ResearchSetupFlowTests.initialize(self)
        with self.assertRaises(ValueError):prepare_fixture(self.config_path,'positive',temporal_case='paper-expire-before-entry')
        self.assertFalse(self.data.exists())
        self.assertFalse(self.cloud.exists())

    def test_existing_case_is_never_replaced(self):
        self.prepare('paper-expire-before-entry')
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError):prepare_fixture(self.config_path,'positive',temporal_case='research-expire-before-robustness')
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def accepted(self,case='paper-expire-after-protection'):
        config,_=self.prepare(case);self.configure()
        owners=LocalOwners(config,namespace='FIXTURE')
        with owners.inbox_factory() as inbox:self.assertEqual(inbox.scan_once(datetime.now(timezone.utc)).accepted,1)
        _,package=owners.resolver.package(SUBMISSION)
        self.owners=owners
        return config,package

    def test_auxiliary_temporal_inputs_must_match_actual_sealed_payload(self):
        config,package=self.accepted();module=self.temporal()
        document=module.read_temporal(config,package)
        self.assertEqual(document['case'],'paper-expire-after-protection')
        path=self.data/'fixture-inputs/temporal.json';original=path.read_bytes()
        value=json.loads(original);value['case']='paper-expire-before-entry';path.write_text(json.dumps(value),encoding='utf-8')
        with self.assertRaises(ValueError):module.read_temporal(config,package)
        path.write_bytes(original);path.unlink()
        with self.assertRaises(ValueError):module.read_temporal(config,package)

    def test_named_clock_resumes_from_original_observation_without_backward_jump(self):
        from application.fixtures.market import FixtureScenarioClock
        config,package=self.accepted();document=self.temporal().read_temporal(config,package)
        clock=FixtureScenarioClock(temporal=document)
        until=datetime.fromisoformat(document['validity']['until'].replace('Z','+00:00'))
        self.assertEqual(clock(),until-timedelta(seconds=2))
        clock.resume((until-timedelta(seconds=1)).isoformat())
        self.assertEqual(clock(),until)
        with self.assertRaises(ValueError):clock.resume((until-timedelta(seconds=4)).isoformat())

    def claim(self):
        owners=self.owners
        with owners.intake_factory() as intake:revision=intake.get_submission(SUBMISSION).revision
        owners.queue.enqueue(SUBMISSION,'r7-synthetic-fixture-policy','temporal-source-enqueue',revision,actor='fixture-owner')
        claim=owners.queue.claim_next()
        owners.queue._checkpoint(claim.run_id,claim.generation,'source-temporal-owner','development')
        return claim

    def test_actual_checkpoint_read_rejects_wrong_owner_run_and_claim_generation(self):
        from application.research.queue import ResearchQueueError
        self.accepted('research-expire-before-robustness');claim=self.claim()
        queue=self.owners.queue
        with self.assertRaises(ResearchQueueError):queue.checkpoint_claim(claim.run_id,claim.generation,'other-owner-run')
        with self.assertRaises(ResearchQueueError):queue.checkpoint_claim(claim.run_id,claim.generation+1,'source-temporal-owner')
        before=queue.get(claim.run_id)
        self.assertEqual(queue.checkpoint_claim(claim.run_id,claim.generation,'source-temporal-owner')['submission_id'],SUBMISSION)
        self.assertEqual(queue.get(claim.run_id),before,'Read must not allocate lease/generation/revision')

    def test_cancel_during_actual_checkpoint_wait_returns_without_fabricating_expiry(self):
        from application.research.queue import ResearchCanceled
        self.accepted('research-expire-before-robustness');claim=self.claim();queue=self.owners.queue
        module=self.temporal();started=time.monotonic()
        def cancel(seconds):
            current=queue.get(claim.run_id)
            queue.cancel(claim.run_id,current['revision'],'temporal-source-cancel',actor='fixture-owner')
        with patch.object(module.time,'sleep',side_effect=cancel) as waited:
            with self.assertRaises(ResearchCanceled):queue._checkpoint(claim.run_id,claim.generation,'source-temporal-owner','robustness')
        waited.assert_called_once()
        self.assertLess(time.monotonic()-started,5)
        self.assertEqual(queue.get(claim.run_id)['state'],'CANCEL_REQUESTED')
        files=list((self.data/'fixture-observations').glob('*.json'))
        self.assertEqual(len(files),1)
        self.assertTrue(files[0].name.endswith('-start.json'))


if __name__=='__main__':unittest.main()
