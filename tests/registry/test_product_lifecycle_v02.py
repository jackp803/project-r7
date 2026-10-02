from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from registry import StrategyIdentity,InvalidTransition,EvidenceGateError
from storage.platform import open_sqlite_platform
from tests.registry.test_validation_lifecycle import strategy_payload,LocalPassE2Boundary

CANONICAL_EDGES={
    ('DRAFT','BACKTESTING'),('DRAFT','RETIRED'),
    ('BACKTESTING','REJECTED'),('BACKTESTING','CANDIDATE'),
    ('CANDIDATE','PAPER'),('CANDIDATE','REJECTED'),('CANDIDATE','RETIRED'),
    ('PAPER','READY_FOR_APPROVAL'),('PAPER','REJECTED'),('PAPER','RETIRED'),
    ('READY_FOR_APPROVAL','APPROVED'),('READY_FOR_APPROVAL','REJECTED'),('READY_FOR_APPROVAL','RETIRED'),
    ('APPROVED','LIVE'),('APPROVED','RETIRED'),('LIVE','DEGRADED'),('LIVE','RETIRED'),
    ('DEGRADED','LIVE'),('DEGRADED','RETIRED')}

class ProductLifecycleModelTests(unittest.TestCase):
    def test_full_canonical_model_has_exact_nineteen_edges_and_ten_states(self):
        from registry import models
        self.assertTrue(hasattr(models,'CANONICAL_LIFECYCLE_TRANSITIONS'),'Missing full authoritative lifecycle model')
        self.assertEqual(CANONICAL_EDGES,set(models.CANONICAL_LIFECYCLE_TRANSITIONS))
        self.assertEqual({'DRAFT','BACKTESTING','CANDIDATE','PAPER','READY_FOR_APPROVAL','APPROVED','LIVE','DEGRADED','REJECTED','RETIRED'},set(models.CANONICAL_LIFECYCLE_STATES))
        for a in models.CANONICAL_LIFECYCLE_STATES:
            for b in models.CANONICAL_LIFECYCLE_STATES:
                self.assertEqual((a,b) in CANONICAL_EDGES,models.is_canonical_lifecycle_transition_allowed(a,b))
    def test_draft_retirement_preserves_definition_and_audits_actor_and_reason(self):
        from contextlib import closing
        import json,sqlite3
        with TemporaryDirectory() as root:
            path=Path(root)/'registry.sqlite'
            with open_sqlite_platform(path,research_namespace='FIXTURE') as service:
                outcome=service.intake(strategy_payload(),source_actor='fixture-inbox')
                self.assertTrue(hasattr(service,'retire'),'Missing named retirement workflow')
                retired=service.retire(outcome.strategy.identity,actor='fixture-operator',reason_codes=('USER_RETIRED',))
                self.assertEqual('RETIRED',retired.current_lifecycle_state)
                self.assertEqual(outcome.strategy.definition_json,retired.definition_json)
                self.assertEqual(1,retired.registry_revision)
                with self.assertRaises(InvalidTransition): service.retire(outcome.strategy.identity,actor='fixture-operator',reason_codes=('USER_RETIRED',))
            with closing(sqlite3.connect(path)) as db:
                row=db.execute('SELECT previous_state,new_state,changed_at,changed_by,reason_codes_json FROM lifecycle_transitions').fetchone()
                self.assertEqual(('DRAFT','RETIRED'),row[:2]); self.assertTrue(row[2].endswith('Z'))
                self.assertEqual('fixture-operator',row[3]); self.assertEqual(['USER_RETIRED'],json.loads(row[4]))
    def test_backtesting_retirement_is_not_a_canonical_edge(self):
        with TemporaryDirectory() as root,open_sqlite_platform(Path(root)/'registry.sqlite',compatibility_boundary=LocalPassE2Boundary()) as service:
            outcome=service.intake(strategy_payload(),source_actor='fixture')
            service.begin_backtesting(outcome.strategy.identity,actor='fixture')
            self.assertTrue(hasattr(service,'retire'),'Missing canonical retirement guard')
            with self.assertRaises(InvalidTransition): service.retire(outcome.strategy.identity,actor='fixture',reason_codes=('USER_RETIRED',))
            self.assertEqual('BACKTESTING',service.get_strategy(outcome.strategy.identity).current_lifecycle_state)

class ProductLegacyBypassTests(unittest.TestCase):
    def _prepare(self, directory, namespace, runtime='0.1.0'):
        from tests.registry.test_validation_lifecycle import backtest_payload,validation_decision_payload
        service = open_sqlite_platform(Path(directory)/'registry.sqlite',
            compatibility_boundary=LocalPassE2Boundary(),research_namespace=namespace)
        payload=strategy_payload(); payload['runtime_compatibility']['runtime_version']=runtime
        outcome=service.intake(payload,source_actor='fixture')
        service.begin_backtesting(outcome.strategy.identity,actor='fixture')
        metadata=dict(verification_status='PASS',verification_kind='LOCAL_EXECUTION',
            source_revision='caller-forged-source',environment='caller',command='caller',result_ref='caller')
        backtest=service.record_backtest_result(backtest_payload(),**metadata)
        decision=service.record_validation_decision(validation_decision_payload('bt-1'),
            backtest_evidence_id=backtest.evidence_id,**metadata)
        return service,outcome.strategy.identity,decision

    def test_product_namespace_cannot_promote_using_legacy_pass_metadata(self):
        for namespace in ('FIXTURE','LOCAL_RESEARCH'):
            with self.subTest(namespace=namespace),TemporaryDirectory() as directory:
                service,identity,decision=self._prepare(directory,namespace)
                with service:
                    with self.assertRaises(EvidenceGateError):
                        service.mark_candidate(identity,actor='caller',validation_evidence_id=decision.evidence_id)
                    self.assertEqual('BACKTESTING',service.get_strategy(identity).current_lifecycle_state)

    def test_direct_store_candidate_bypass_requires_product_owner_evidence(self):
        from registry.models import LifecycleTransitionRecord
        with TemporaryDirectory() as directory:
            service,identity,decision=self._prepare(directory,'FIXTURE')
            transition=LifecycleTransitionRecord('forged-transition',identity,'BACKTESTING','CANDIDATE',
                '2026-10-02T00:00:00Z','caller',('CALLER_PASS',),decision.evidence_id,1,2)
            with service:
                with self.assertRaises(EvidenceGateError): service._store.append_transition(transition)
                self.assertEqual('BACKTESTING',service.get_strategy(identity).current_lifecycle_state)

    def test_v02_subject_cannot_escape_product_gates_in_unclassified_legacy_registry(self):
        with TemporaryDirectory() as directory:
            service,identity,decision=self._prepare(directory,None,runtime='0.2.0')
            with service,self.assertRaises(EvidenceGateError):
                service.mark_candidate(identity,actor='caller',validation_evidence_id=decision.evidence_id)
