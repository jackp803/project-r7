"""Fixture-only lifecycle mechanics, never operational LIVE authorization."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib,json,unittest

from application.research.service import ResearchService
from application.research.compatibility import ExecutedCompatibilityBoundary
from application.research.product_assessment import ExecutedProductAssessmentBoundary
from registry import StrategyIdentity,EvidenceGateError,ConcurrencyConflict,InvalidTransition
from registry.models import LifecycleTransitionRecord
from storage.platform import open_sqlite_platform
from tests.registry.test_product_lifecycle_v02 import CANONICAL_EDGES
from tests.application.test_research_robustness import selected
from tests.application.test_product_assessment_binding import risk_fixture
from tests.application.dataset_fixtures import encoded
from tests.validation.robustness_fixtures import subject


class OperationalLifecycleTests(unittest.TestCase):
    def api(self):
        try: return importlib.import_module('registry.operational_authority')
        except ModuleNotFoundError: self.fail('Missing guarded operational lifecycle authority')

    def fixture(self,root):
        api=self.api(); selected(root); (Path(root)/'risk.json').write_bytes(encoded(risk_fixture()))
        research=ResearchService(local_root=root,database_path=Path(root)/'research.sqlite',
            registry_path=Path(root)/'research-registry.sqlite',namespace='FIXTURE',owner_id='fixture')
        result=research.run(submission_id='fixture',definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',
            cost_policy_ref='cost.json',research_policy_ref='research.json',robustness_policy_ref='robustness.json',
            family_id='fixture-family',seed=42,risk_policy_ref='risk.json')
        with open_sqlite_platform(Path(root)/'research-registry.sqlite',research_namespace='FIXTURE') as e6:
            product=e6.product_assessment(result.run_id)
        clock=[datetime(2026,10,3,tzinfo=timezone.utc)]
        from strategy.v02.capabilities import _revision,build_capability_snapshot
        release=[api.ReleaseBinding(namespace='FIXTURE',implementation_hash=_revision(),
            executable_revision=research.report(result.run_id)['provenance']['executable_revision'],
            build_hash='sha256:'+'1'*64,config_hash='sha256:'+'2'*64,config_generation=1,
            capability_hash=build_capability_snapshot().snapshot_hash,provider_profile_hash='sha256:'+'3'*64,
            provider_ref='fixture-paper',account_ref='fixture-account',risk_policy_hash=product.risk_policy_hash,
            risk_generation=1,runtime_generation=1,release_kind='FIXTURE')]
        auth=api.HumanAuthenticator(namespace='FIXTURE',reauth_seconds=300,clock=lambda:clock[0],
            verifier=lambda proof:api.HumanIdentity('fixture-owner',('ProductOwner',)) if proof=='FIXTURE_AUTH_PROOF' else None)
        from tests.validation.test_paper_promotion_policy import policy_fixture
        from validation.paper_policy import parse_paper_promotion_policy
        selected_paper=parse_paper_promotion_policy(policy_fixture(),namespace='FIXTURE')
        def resolve(kind,reference,identity):
            body=dict(evidence_ref=reference,execution='SIMULATED_MECHANICS',
                paper_policy_ref='fixture-paper-policy',policy_hash=selected_paper.policy_hash,actual_elapsed_seconds=0,closed_trades=7,
                entries_enabled=False,broker_kind='PAPER_ONLY',forward_mode='ACCELERATED_FIXTURE')
            return api.OwnerEvidence(kind,identity,product.strategy_content_hash,release[0],json.dumps(body))
        boundary=api.ProductLifecycleComposition(namespace='FIXTURE',current_release=lambda:release[0],
            resolve_evidence=resolve,authenticator=auth,clock=lambda:clock[0])
        boundary.select_paper_policy('fixture-paper-policy',policy_fixture())
        envelope=dict(schema_version='r7-deployment-envelope-v0.2',envelope_id='FIXTURE_ENVELOPE',namespace='FIXTURE',
            strategy_id=product.identity.strategy_id,strategy_version=product.identity.strategy_version,
            strategy_content_hash=product.strategy_content_hash,release=release[0].as_dict(),symbol=subject()['symbol'],
            capital_ceiling_usdt='100',risk_per_trade_usdt='1',max_positions=1,daily_loss_limit_usdt='5',
            aggregate_loss_limit_usdt='10',permissions=['MANAGE_EXISTING','NEW_EXPOSURE'],generation=1,
            valid_from=clock[0].isoformat(),expires_at=(clock[0]+timedelta(hours=1)).isoformat())
        boundary.register_envelope('fixture-envelope',envelope)
        import jsonschema
        schema=json.loads((Path(__file__).resolve().parents[2]/'contracts/deployment_envelope_v0_2.schema.json').read_text())
        jsonschema.Draft202012Validator(schema).validate(envelope)
        return api,research,result.run_id,product.identity,boundary,auth,clock,release,envelope

    def platform(self,root,research,run_id,boundary,name):
        return open_sqlite_platform(Path(root)/(name+'.sqlite'),research_namespace='FIXTURE',
            compatibility_boundary=ExecutedCompatibilityBoundary(research.journal,run_id,subject()['content_hash']),
            product_assessment_boundary=ExecutedProductAssessmentBoundary(research.journal,research.ledger,'FIXTURE'),
            lifecycle_boundary=boundary)

    def apply(self,e6,identity,target,auth,*,command='command'):
        current=e6.get_strategy(identity)
        kwargs=dict(command_id=command,expected_revision=current.registry_revision)
        if target=='BACKTESTING': return e6.begin_backtesting(identity,actor='fixture')
        if target=='CANDIDATE':
            record=e6.record_product_assessment(identity,run_id=self.run_id,actor='fixture')
            return e6.get_strategy(identity)
        if target=='PAPER': return e6.start_paper(identity,evidence_ref='fixture-paper-start',actor='fixture',**kwargs)
        if target=='READY_FOR_APPROVAL': return e6.mark_ready_for_approval(identity,evidence_ref='fixture-forward',actor='fixture',**kwargs)
        if target=='APPROVED':
            return e6.record_approval(identity,envelope_ref='fixture-envelope',authenticated_human=auth.authenticate('FIXTURE_AUTH_PROOF'),
                decision='APPROVE',reason='Fixture consent mechanics',**kwargs)
        if target=='LIVE':
            human=auth.authenticate('FIXTURE_AUTH_PROOF')
            method=e6.resume_authorized if current.current_lifecycle_state=='DEGRADED' else e6.activate_deployment
            return method(identity,evidence_ref='fixture-admission',authenticated_human=human,**kwargs)
        if target=='DEGRADED': return e6.degrade(identity,actor='fixture-monitor',reason_codes=('HEARTBEAT_STALE',),**kwargs)
        if target=='RETIRED': return e6.retire(identity,actor='fixture',reason_codes=('USER_RETIRED',))
        if target=='REJECTED': return e6.reject(identity,actor='fixture',reason_codes=('USER_REJECTED',),**kwargs)

    def build(self,e6,identity,state,auth):
        e6.intake(subject(),source_actor='fixture')
        path=['BACKTESTING','CANDIDATE','PAPER','READY_FOR_APPROVAL','APPROVED','LIVE','DEGRADED']
        if state=='DRAFT': return
        if state in ('REJECTED','RETIRED'):
            for target in path[:2]: self.apply(e6,identity,target,auth,command='build-'+target)
            self.apply(e6,identity,state,auth,command='build-'+state); return
        for target in path[:path.index(state)+1]: self.apply(e6,identity,target,auth,command='build-'+target)

    def test_all_operational_legal_edges_and_every_illegal_pair_use_owner_storage(self):
        from registry.models import CANONICAL_LIFECYCLE_STATES
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            with research:
                for source in CANONICAL_LIFECYCLE_STATES:
                    with self.platform(root,research,self.run_id,boundary,source) as e6:
                        self.build(e6,identity,source,auth)
                        for target in CANONICAL_LIFECYCLE_STATES:
                            if (source,target) in CANONICAL_EDGES: continue
                            record=e6.get_strategy(identity)
                            forged=LifecycleTransitionRecord('illegal-'+source+'-'+target,identity,source,target,
                                clock[0].isoformat(),'caller',('SKIP',),None,record.registry_revision,record.registry_revision+1)
                            with self.subTest(source=source,target=target),self.assertRaises(InvalidTransition):
                                e6._store.append_transition(forged)
                        self.assertEqual(source,e6.get_strategy(identity).current_lifecycle_state)
                for index,(source,target) in enumerate(sorted(CANONICAL_EDGES)):
                    if source=='BACKTESTING' and target=='REJECTED': continue # actual quantitative case is in product binding tests
                    with self.subTest(source=source,target=target),self.platform(root,research,self.run_id,boundary,'edge-'+str(index)) as e6:
                        self.build(e6,identity,source,auth)
                        before=e6.get_strategy(identity)
                        after=self.apply(e6,identity,target,auth)
                        self.assertEqual(target,after.current_lifecycle_state)
                        self.assertEqual(before.registry_revision+1,after.registry_revision)
                        self.assertEqual(before.definition_json,after.definition_json)

    def test_forged_stale_wrong_subject_and_revoked_approval_fail_closed(self):
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            with research,self.platform(root,research,self.run_id,boundary,'security') as e6:
                self.build(e6,identity,'READY_FOR_APPROVAL',auth)
                revision=e6.get_strategy(identity).registry_revision
                kwargs=dict(envelope_ref='fixture-envelope',decision='APPROVE',reason='fixture',command_id='approve',expected_revision=revision)
                for forged in ('ProductOwner',{'actor':'ProductOwner'},None):
                    with self.subTest(forged=forged),self.assertRaises(EvidenceGateError):
                        e6.record_approval(identity,authenticated_human=forged,**kwargs)
                human=auth.authenticate('FIXTURE_AUTH_PROOF')
                with self.assertRaises(ConcurrencyConflict):
                    e6.record_approval(identity,authenticated_human=human,**dict(kwargs,expected_revision=revision-1))
                wrong=dict(envelope,strategy_version='wrong'); boundary.register_envelope('wrong',wrong)
                with self.assertRaises(EvidenceGateError):
                    e6.record_approval(identity,authenticated_human=human,**dict(kwargs,envelope_ref='wrong'))
                approved=e6.record_approval(identity,authenticated_human=human,**kwargs)
                approval=e6._store.latest_human_approval(identity)
                self.assertEqual('fixture-owner',approval.actor); self.assertEqual('FIXTURE',approval.namespace)
                with self.assertRaises(EvidenceGateError): e6._store._save_owner_record(approval,capability=object())
                import sqlite3
                from contextlib import closing
                with closing(sqlite3.connect(Path(root)/'security.sqlite')) as db:
                    with self.assertRaises(sqlite3.IntegrityError): db.execute("UPDATE human_approvals SET actor='ProductOwner'")
                    with self.assertRaises(sqlite3.IntegrityError): db.execute('DELETE FROM human_approvals')
                e6.revoke_approval(identity,authenticated_human=human,reason='fixture revoked',command_id='revoke')
                with self.assertRaises(EvidenceGateError):
                    e6.activate_deployment(identity,evidence_ref='fixture-admission',authenticated_human=human,
                        command_id='activate',expected_revision=approved.registry_revision)
                self.assertEqual('APPROVED',e6.get_strategy(identity).current_lifecycle_state)

    def test_direct_store_operational_skip_and_restart_cannot_resume_live(self):
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            with research:
                with self.platform(root,research,self.run_id,boundary,'restart') as e6:
                    self.build(e6,identity,'DEGRADED',auth)
                    record=e6.get_strategy(identity)
                    forged=LifecycleTransitionRecord('forged-resume',identity,'DEGRADED','LIVE',clock[0].isoformat(),
                        'ProductOwner',('NEW_SIGNAL',),None,record.registry_revision,record.registry_revision+1)
                    with self.assertRaises(EvidenceGateError): e6._store.append_transition(forged)
                with open_sqlite_platform(Path(root)/'restart.sqlite',research_namespace='FIXTURE') as restarted:
                    self.assertEqual('DEGRADED',restarted.get_strategy(identity).current_lifecycle_state)
                    with self.assertRaises(EvidenceGateError):
                        restarted.resume_authorized(identity,evidence_ref='fixture-admission',authenticated_human={'actor':'ProductOwner'},
                            command_id='restart-resume',expected_revision=record.registry_revision)

    def test_approval_transition_and_command_receipt_are_atomic_and_retryable(self):
        from unittest.mock import patch
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            with research,self.platform(root,research,self.run_id,boundary,'atomic') as e6:
                self.build(e6,identity,'READY_FOR_APPROVAL',auth)
                before=e6.get_strategy(identity)
                kwargs=dict(envelope_ref='fixture-envelope',authenticated_human=auth.authenticate('FIXTURE_AUTH_PROOF'),
                    decision='APPROVE',reason='fixture',command_id='atomic-approve',expected_revision=before.registry_revision)
                with patch.object(e6._store,'append_transition',side_effect=RuntimeError('fixture crash before owner transition')):
                    with self.assertRaises(RuntimeError): e6.record_approval(identity,**kwargs)
                self.assertIsNone(e6._store.latest_human_approval(identity),'Orphan approval survived failed owner transaction')
                self.assertEqual(before,e6.get_strategy(identity))
                clock[0]+=timedelta(seconds=1)
                first=e6.record_approval(identity,**kwargs)
                clock[0]+=timedelta(seconds=1)
                try: second=e6.record_approval(identity,**kwargs)
                except Exception as exc: self.fail('Completed identical approval command did not return its original receipt: '+type(exc).__name__)
                self.assertEqual(first,second)
                with self.assertRaises(EvidenceGateError):
                    e6.record_approval(identity,**dict(kwargs,reason='changed consent'))

    def test_expired_human_and_changed_release_generation_cannot_approve_or_activate(self):
        from dataclasses import replace
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            with research,self.platform(root,research,self.run_id,boundary,'expiry') as e6:
                self.build(e6,identity,'READY_FOR_APPROVAL',auth)
                revision=e6.get_strategy(identity).registry_revision
                human=auth.authenticate('FIXTURE_AUTH_PROOF'); clock[0]+=timedelta(seconds=301)
                with self.assertRaises(EvidenceGateError):
                    e6.record_approval(identity,envelope_ref='fixture-envelope',authenticated_human=human,
                        decision='APPROVE',reason='fixture',command_id='expired-human',expected_revision=revision)
                approved=e6.record_approval(identity,envelope_ref='fixture-envelope',authenticated_human=auth.authenticate('FIXTURE_AUTH_PROOF'),
                    decision='APPROVE',reason='fixture',command_id='fresh-human',expected_revision=revision)
                original=release[0]
                for field in ('config_generation','runtime_generation','risk_generation'):
                    release[0]=replace(original,**{field:2})
                    with self.subTest(field=field),self.assertRaises(EvidenceGateError):
                        e6.activate_deployment(identity,evidence_ref='fixture-admission',authenticated_human=auth.authenticate('FIXTURE_AUTH_PROOF'),
                            command_id='stale-'+field,expected_revision=approved.registry_revision)
                release[0]=original; clock[0]+=timedelta(hours=1)
                with self.assertRaises(EvidenceGateError):
                    e6.activate_deployment(identity,evidence_ref='fixture-admission',authenticated_human=auth.authenticate('FIXTURE_AUTH_PROOF'),
                        command_id='expired-envelope',expected_revision=approved.registry_revision)
                self.assertEqual('APPROVED',e6.get_strategy(identity).current_lifecycle_state)

    def test_identical_completed_approval_command_returns_original_receipt(self):
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            with research,self.platform(root,research,self.run_id,boundary,'receipt') as e6:
                self.build(e6,identity,'READY_FOR_APPROVAL',auth)
                kwargs=dict(envelope_ref='fixture-envelope',authenticated_human=auth.authenticate('FIXTURE_AUTH_PROOF'),
                    decision='APPROVE',reason='fixture',command_id='approve-once',expected_revision=e6.get_strategy(identity).registry_revision)
                first=e6.record_approval(identity,**kwargs)
                clock[0]+=timedelta(seconds=1)
                try: second=e6.record_approval(identity,**kwargs)
                except Exception as exc: self.fail('Identical completed command was replayed as a new transition: '+type(exc).__name__)
                self.assertEqual(first,second)

    def test_paper_start_requires_selected_local_promotion_policy(self):
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            if hasattr(boundary,'_paper_policies'): boundary._paper_policies.clear()
            with research,self.platform(root,research,self.run_id,boundary,'missing-paper-policy') as e6:
                self.build(e6,identity,'CANDIDATE',auth)
                with self.assertRaises(EvidenceGateError):
                    e6.start_paper(identity,evidence_ref='fixture-paper-start',actor='fixture',command_id='missing-policy',expected_revision=2)
                self.assertEqual('CANDIDATE',e6.get_strategy(identity).current_lifecycle_state)

    def test_changed_paper_policy_cannot_transplant_old_ready_evidence_into_approval(self):
        from tests.validation.test_paper_promotion_policy import policy_fixture
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            with research,self.platform(root,research,self.run_id,boundary,'policy-amendment') as e6:
                self.build(e6,identity,'READY_FOR_APPROVAL',auth)
                amended=policy_fixture(); amended['generation']=2; amended['min_closed_trades']=100
                boundary.select_paper_policy('new-forward-policy',amended)
                with self.assertRaises(EvidenceGateError):
                    e6.record_approval(identity,envelope_ref='fixture-envelope',authenticated_human=auth.authenticate('FIXTURE_AUTH_PROOF'),
                        decision='APPROVE',reason='fixture',command_id='old-forward',expected_revision=4)
                self.assertEqual('READY_FOR_APPROVAL',e6.get_strategy(identity).current_lifecycle_state)

    def test_retirement_preserves_existing_owner_exposure_and_protection_graph(self):
        import sqlite3
        from contextlib import closing
        from storage.runtime import open_paper_runtime_journal
        from tests.storage.test_paper_runtime_durability import PaperRuntimeDurabilityDefinitions,risk_decision,approved_plan
        with TemporaryDirectory() as root:
            api,research,self.run_id,identity,boundary,auth,clock,release,envelope=self.fixture(root)
            path=Path(root)/'retirement.sqlite'
            with research,self.platform(root,research,self.run_id,boundary,'retirement') as e6:
                self.build(e6,identity,'PAPER',auth)
                with open_paper_runtime_journal(path) as journal:
                    fixture=PaperRuntimeDurabilityDefinitions('runTest'); fixture.journal=journal
                    def historical_core():
                        # Explicit persisted historical fixtures; no broker or risk evaluation is started.
                        risk=risk_decision(); plan=approved_plan()
                        for value in (risk,plan): value.update(strategy_id=identity.strategy_id,strategy_version=identity.strategy_version)
                        journal.persist_risk_decision(risk); journal.persist_approved_trade_plan(plan)
                        return risk,plan
                    fixture._persist_core=historical_core
                    graph=fixture._persist_open_protection_graph()
                    recovery=journal.recover(position_id=graph['protected']['position_id'])
                    with closing(sqlite3.connect(path)) as db:
                        tables=[row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name LIKE 'paper_runtime_%' ORDER BY name")]
                        before={name:db.execute('SELECT * FROM '+name).fetchall() for name in tables}
                    retired=e6.retire(identity,actor='fixture',reason_codes=('USER_RETIRED',))
                    self.assertEqual('RETIRED',retired.current_lifecycle_state)
                    self.assertEqual(recovery,journal.recover(position_id=graph['protected']['position_id']))
                    with closing(sqlite3.connect(path)) as db:
                        self.assertEqual(before,{name:db.execute('SELECT * FROM '+name).fetchall() for name in tables})
