"""Resolve actual immutable E3 job/holdout evidence for the E6 composition.

Only configured local owner journals enter here. Request bodies provide run IDs,
never a result payload or a PASS status. Resolution happens outside E6 locks.
"""
from dataclasses import dataclass

from registry import EvidenceGateError
from registry.product_assessment import canonical,digest
from strategy.v02.capabilities import _revision
from application.research.evidence import ResearchJournal
from application.research.holdout import ResearchTrialLedger,FrozenFinalist


@dataclass(frozen=True)
class ResolvedProductAssessment:
    run_id: str
    namespace: str
    inputs_json: str
    assessment_json: str


class ExecutedProductAssessmentBoundary:
    def __init__(self,journal,ledger,namespace):
        if not isinstance(journal,ResearchJournal) or not isinstance(ledger,ResearchTrialLedger) or namespace not in ('FIXTURE','LOCAL_RESEARCH'):
            raise EvidenceGateError('Actual configured research owner journals required')
        self._journal=journal; self._ledger=ledger; self._namespace=namespace

    def resolve(self,run_id):
        inputs,input_hash=self._ledger._run(run_id)
        if inputs['namespace']!=self._namespace or inputs['implementation_hash']!=_revision():
            raise EvidenceGateError('Research namespace or executable source changed')
        provenance=inputs['provenance']
        if provenance['implementation_hash']!=inputs['implementation_hash'] or provenance['execution']!='LOCAL':
            raise EvidenceGateError('Actual local executable provenance required')
        if self._namespace=='LOCAL_RESEARCH' and (provenance['worktree']!='CLEAN' or provenance['executable_revision'] is None):
            raise EvidenceGateError('Real research promotion requires exact clean source')
        robustness,robust_hash=self._ledger._robustness(run_id)
        if robustness['strategy_content_hash']!=inputs['strategy']['content_hash'] or robustness['namespace']!=self._namespace:
            raise EvidenceGateError('Robustness subject mismatch')
        product=self._journal.result(run_id,'sealed_oos')
        if product is None:
            if robustness['status']=='PASS': raise EvidenceGateError('Complete sealed OOS required after robustness PASS')
            product=dict(schema_version='r7-product-assessment-v0.2',run_id=run_id,namespace=self._namespace,
                strategy_content_hash=inputs['strategy']['content_hash'],status=robustness['status'],
                reason_codes=robustness['reason_codes'],independent_oos=False,sealed_backtest=None,
                canonical_oos_decision=None,robustness_hash=robust_hash,provenance=provenance,
                raw_result_hashes=robustness['raw_result_hashes'])
        else:
            row=self._ledger._db.execute('SELECT * FROM research_finalists WHERE run_id=?',(run_id,)).fetchone()
            if row is None: raise EvidenceGateError('Immutable finalist missing')
            frozen=FrozenFinalist(row['finalist_id'],row['frozen_json'],row['frozen_hash'])
            value=self._ledger.verify_finalist(frozen)
            stored=self._ledger.result(frozen)
            if stored is None or stored.as_dict()!=product or value['run_input_hash']!=input_hash or value['robustness_hash']!=robust_hash:
                raise EvidenceGateError('Actual sealed result/finalist lineage mismatch')
            if value['provenance']!=provenance or value['strategy']!=inputs['strategy']:
                raise EvidenceGateError('Frozen source/strategy mismatch')
        if product['run_id']!=run_id or product['namespace']!=self._namespace or product['strategy_content_hash']!=inputs['strategy']['content_hash']:
            raise EvidenceGateError('Product assessment subject mismatch')
        if product['status'] not in ('PASS','FAIL','BLOCKED'):
            raise EvidenceGateError('Unperformed assessment cannot become evidence')
        return ResolvedProductAssessment(run_id,self._namespace,canonical(inputs),canonical(product))
