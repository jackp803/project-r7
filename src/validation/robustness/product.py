"""E3 combined product assessment from an executed finalist and final replay."""
from decimal import localcontext
from indicators.v02.common import REFERENCE_CONTEXT
from validation.oos import ValidationSubject,OOSValidationContext,evaluate_oos_validation
from .common import assessment,digest,fail
from .policies import ResearchPolicy,assess_partition

def assess_final_replay(*,finalist,robustness,backtest,source_verification,trial_count):
    if source_verification['scope']!='FULL_LOGICAL_VERIFIED' or source_verification['manifest_hash']!=finalist['dataset_manifest_hash']:
        fail('HOLDOUT_SOURCE_NOT_VERIFIED')
    if backtest['strategy_content_hash']!=finalist['strategy_content_hash']: fail('OOS_STRATEGY_CONTENT_HASH_MISMATCH')
    with localcontext(REFERENCE_CONTEXT):
        policy=ResearchPolicy.parse(finalist['policies']['research'])
        subject=ValidationSubject(backtest['strategy_id'],backtest['strategy_version'],backtest['backtest_result_id'])
        development=robustness['development']['backtest']
        thresholds=policy.validation_policy('sealed_oos')
        context=OOSValidationContext(finalist['split_policy_hash'],backtest['dataset_id'],backtest['dataset_hash'],
            backtest['dataset_start'],backtest['dataset_end'],development['dataset_id'],development['dataset_hash'],thresholds.version)
        canonical_decision=evaluate_oos_validation(subject=subject,backtest_result=backtest,context=context,policy=thresholds,
            execution_state='EXECUTED',decided_at=finalist['frozen_at']).to_contract()
        product_decision=assess_partition(backtest,policy,'sealed_oos')
        reasons=list(robustness['reason_codes'])+product_decision['reason_codes']
        # The canonical legacy evaluator deliberately retains its existing FAIL
        # vocabulary. Product sample adequacy dominates that legacy numeric FAIL.
        status=product_decision['status']
        if canonical_decision['decision']=='BLOCKED': status='BLOCKED'; reasons+=canonical_decision['reason_codes']
        elif canonical_decision['decision']=='FAIL' and status!='BLOCKED': status='FAIL'; reasons+=canonical_decision['reason_codes']
        if robustness['status']=='BLOCKED': status='BLOCKED'
        elif robustness['status']=='FAIL' and status!='BLOCKED': status='FAIL'
        return assessment(dict(schema_version='r7-product-assessment-v0.2',status=status,reason_codes=sorted(set(reasons)),
            finalist_id=finalist['finalist_id'],run_id=finalist['run_id'],strategy_content_hash=finalist['strategy_content_hash'],
            namespace=finalist['namespace'],independent_oos=True,sealed_backtest=backtest,canonical_oos_decision=canonical_decision,
            sealed_product_decision=product_decision,robustness_hash=digest(robustness),policy_hashes=finalist['policy_hashes'],
            sealed_dataset_verification=source_verification,
            raw_result_hashes=robustness['raw_result_hashes']+[digest(backtest),digest(canonical_decision),digest(product_decision),digest(source_verification)],
            trial_count=trial_count,selection_procedure=robustness['selection_procedure'],provenance=finalist['provenance'],
            limitations=robustness['limitations']+['One observed final holdout is not reusable independent evidence',
                'Finite historical research is not forward PAPER/provider verification or financial authorization']))
