"""Tactical request expiry through actual product-selected intake/research owners."""
from datetime import datetime,timedelta,timezone
import json,unittest
import sys
from pathlib import Path

from application.cloud.manifest import canonical_bytes
from application.local_owners import LocalOwners
from application.research.queue import ResearchQueueError
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from registry import StrategyIdentity
from tests.application import test_fixture_recipe_flow as recipe

NOW=datetime(2026,10,5,tzinfo=timezone.utc)
UNTIL=NOW+timedelta(seconds=2)
def z(value):return value.isoformat().replace('+00:00','Z')

class SubmissionValidityResearchTests(unittest.TestCase):
    setUp=recipe.FixtureRecipeFlowTests.setUp
    call=recipe.FixtureRecipeFlowTests.call
    initialize=recipe.FixtureRecipeFlowTests.initialize
    generate=recipe.FixtureRecipeFlowTests.generate
    prepare=recipe.FixtureRecipeFlowTests.prepare
    configure=recipe.FixtureRecipeFlowTests.configure

    def selected(self):
        config,generated=self.prepare()
        # Change only the fresh unexecuted author envelope, before any intake.
        # E2 definition/hash, market/policies and all actual results stay untouched.
        path=next(self.cloud.rglob('manifest.json'));manifest=json.loads(path.read_bytes())
        manifest.update(intent_class='TACTICAL_STRATEGY',validity={'from':z(NOW),'until':z(UNTIL)})
        path.write_bytes(canonical_bytes(manifest));self.configure()
        self.clock=[NOW];owners=LocalOwners(config,namespace='FIXTURE',clock=lambda:self.clock[0])
        with owners.inbox_factory() as inbox:self.assertEqual(inbox.scan_once(NOW).accepted,1)
        self.submission=generated['submission_id'];self.policy=generated['policy_id']
        self.identity=StrategyIdentity(manifest['strategy_id'],manifest['strategy_version'])
        with owners.intake_factory() as intake:
            self.submission_revision=intake.get_submission(self.submission).revision
            self.receipt=intake.accepted_receipt(self.submission)
        return owners

    def enqueue(self,owners,command='validity-enqueue'):
        return owners.queue.enqueue(self.submission,self.policy,command,self.submission_revision,actor='fixture-owner')

    def retained(self,owners,lifecycle):
        with owners.intake_factory() as intake:self.assertEqual(intake.accepted_receipt(self.submission),self.receipt)
        with owners.registry_factory() as e6:self.assertEqual(e6.get_strategy(self.identity).current_lifecycle_state,lifecycle)

    def test_expired_accepted_envelope_denies_new_research_but_keeps_author_context(self):
        owners=self.selected();self.clock[0]=UNTIL
        with self.assertRaises(ResearchQueueError) as denied:self.enqueue(owners)
        self.assertEqual(denied.exception.code,'SUBMISSION_EXPIRED')
        self.assertEqual(owners.queue.list(),[])
        self.assertEqual(owners.resolver.manifest_view(self.submission)['validity']['until'],z(UNTIL))
        self.retained(owners,'DRAFT')

    def test_expiry_after_enqueue_is_terminal_without_research_or_intake_rewrite(self):
        owners=self.selected();receipt=self.enqueue(owners);before=owners.queue.get(receipt['run_id'])
        self.clock[0]=UNTIL;claim=owners.queue.claim_next();result=owners.queue.step(claim.run_id,claim.generation)
        self.assertEqual(result['state'],'EXPIRED')
        self.assertEqual(result['reason_codes'],['SUBMISSION_EXPIRED'])
        self.assertIsNone(result['owner_run_id']);self.assertIsNone(result['outcome'])
        self.assertEqual(result['input_hash'],before['input_hash'])
        self.assertFalse((self.data/'research.sqlite').exists())
        self.assertIsNone(owners.queue.claim_next())
        self.assertEqual(self.enqueue(owners),receipt,'Immutable retry receipt is history,never renewed authority')
        self.retained(owners,'DRAFT')

    def test_expiry_at_first_checkpoint_creates_no_replay_or_backtest_transition(self):
        owners=self.selected();receipt=self.enqueue(owners)
        owners.queue.stage_observer=lambda run,stage:self.clock.__setitem__(0,UNTIL)
        claim=owners.queue.claim_next();result=owners.queue.step(claim.run_id,claim.generation)
        self.assertEqual(result['state'],'EXPIRED')
        self.assertEqual(result['reason_codes'],['SUBMISSION_EXPIRED'])
        with owners.queue.service_factory() as owner:self.assertEqual(owner.journal.attempts(result['owner_run_id']),[])
        self.retained(owners,'DRAFT')

    def expire_at_stage(self,stage):
        owners=self.selected();self.enqueue(owners)
        def expire(run,current):
            if current==stage:self.clock[0]=UNTIL
        owners.queue.stage_observer=expire
        claim=owners.queue.claim_next();result=owners.queue.step(claim.run_id,claim.generation)
        self.assertEqual(result['state'],'EXPIRED')
        self.assertEqual(result['reason_codes'],['SUBMISSION_EXPIRED'])
        self.assertIsNone(result['outcome']);self.assertIsNone(owners.queue.claim_next())
        self.retained(owners,'BACKTESTING')
        with owners.registry_factory() as e6:self.assertIsNone(e6.product_assessment(result['owner_run_id']))
        return owners,result

    def test_expiry_before_robustness_keeps_actual_development_evidence_without_oos(self):
        owners,result=self.expire_at_stage('robustness')
        with owners.queue.service_factory() as owner:
            self.assertIsNotNone(owner.journal.result(result['owner_run_id'],'development_replay'))
            self.assertIsNotNone(owner.journal.result(result['owner_run_id'],'e6_backtest_persistence'))
            self.assertIsNone(owner.journal.result(result['owner_run_id'],'robustness'))
            self.assertIsNone(owner.journal.result(result['owner_run_id'],'sealed_oos'))

    def test_expiry_before_candidate_assessment_keeps_sealed_oos_without_candidate(self):
        owners,result=self.expire_at_stage('e6_product_assessment')
        with owners.queue.service_factory() as owner:
            self.assertIsNotNone(owner.journal.result(result['owner_run_id'],'sealed_oos'))
            self.assertIsNone(owner.journal.result(result['owner_run_id'],'e6_product_assessment'))

    def test_exclusive_upper_boundary_admits_one_microsecond_before_expiry(self):
        owners=self.selected();self.clock[0]=UNTIL-timedelta(microseconds=1)
        self.assertEqual(self.enqueue(owners)['status'],'QUEUED')
        self.retained(owners,'DRAFT')

    def test_reaped_worker_parent_keeps_expired_terminal_disposition(self):
        owners=self.selected();self.enqueue(owners);self.clock[0]=UNTIL
        claim=owners.queue.claim_next();expired=owners.queue.step(claim.run_id,claim.generation)
        self.assertEqual(expired['state'],'EXPIRED')
        owned=spawn_owned([sys.executable,'-c','pass'],cwd=Path.cwd(),limits=ResourceLimits(5))
        try:
            self.assertEqual(owned.wait(),0)
            self.assertTrue(terminate_owned(owned,deadline_seconds=5).reaped)
            self.assertEqual(owners.queue.finish_terminated_worker(claim,owned),expired)
        finally:self.assertTrue(terminate_owned(owned,deadline_seconds=5).reaped)

if __name__=='__main__':unittest.main()
