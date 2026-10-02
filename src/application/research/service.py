"""Actual immutable E1 -> E2 -> E3 -> E6 local research composition.

This stage computes development diagnostics. S07/S08 own complete product
assessment and promotion. No author-supplied result or decision is accepted.
"""
from dataclasses import dataclass,asdict,replace
import json
from pathlib import Path
from decimal import localcontext

from application.datasets.catalog import DatasetCatalog,canonical,decode,digest,exact,fail,positive_int,read_local,text
from application.datasets.resolver import DatasetResolver
from application.datasets.split_plan import resolve_split,resolve_split_manifest
from application.research.compatibility import ExecutedCompatibilityBoundary,execute_compatibility
from application.research.evidence import ResearchJournal,capture_provenance,now_utc
from application.research.orchestrator import ResearchOrchestrator
from application.research.holdout import ResearchTrialLedger,SealedOOSBinding,evaluate_sealed_oos
from application.platform.resources import inspect_hardware,ResourcePolicy
from backtest.costs import FeeModel,SlippageModel
from backtest.e2_runtime import project_e2_runtime_binding
from backtest.replay import DatasetDescriptor,HistoricalReplayEngine,ReplayConfig
from indicators.v02.common import finite_decimal,REFERENCE_CONTEXT
from registry import StrategyIdentity
from storage.platform import open_sqlite_platform
from strategy import parse_strategy_definition
from strategy.v02.models import ParsedStrategyV02
from validation.robustness.evaluator import DevelopmentBinding,evaluate_robustness
from validation.robustness.policies import ResearchPolicy,parse_robustness_policy
from validation.robustness.common import integer as research_integer

class ResearchError(ValueError):
    def __init__(self,code): self.code=code; super().__init__(code)

@dataclass(frozen=True)
class ResearchOutcome:
    run_id: str
    status: str
    reason_codes: tuple
    compatibility_status: str
    strategy_lifecycle: str

def _cost_policy(value,namespace):
    value=json.loads(canonical(value))
    exact(value,('schema_version','policy_id','generation','namespace','cost_model_version','fixed_quantity','quantity_unit',
                 'fee_unit','maker_bps','taker_bps','slippage_unit','entry_bps','exit_bps','max_evaluations'))
    if value['schema_version']!='r7-replay-cost-policy-v0.2' or value['namespace']!=namespace: raise ResearchError('COST_POLICY_PROFILE_MISMATCH')
    if value['quantity_unit']!='BASE' or value['fee_unit']!='BPS_OF_NOTIONAL' or value['slippage_unit']!='BPS_OF_REFERENCE_PRICE': raise ResearchError('UNSUPPORTED_COST_UNITS')
    for key in ('policy_id','cost_model_version'): text(value[key])
    positive_int(value['generation'],2147483647); positive_int(value['max_evaluations'],2000)
    for key in ('fixed_quantity','maker_bps','taker_bps','entry_bps','exit_bps'): finite_decimal(value[key])
    if finite_decimal(value['fixed_quantity'])<=0: raise ResearchError('INVALID_RESEARCH_QUANTITY')
    FeeModel(value['cost_model_version'],value['maker_bps'],value['taker_bps'])
    SlippageModel(value['cost_model_version'],value['entry_bps'],value['exit_bps'])
    return value

class ResearchService:
    def __init__(self,*,local_root,database_path,registry_path,namespace,owner_id):
        if namespace not in ('FIXTURE','LOCAL_RESEARCH'): raise ResearchError('INVALID_NAMESPACE')
        self.root=Path(local_root).absolute(); self.registry_path=Path(registry_path).absolute()
        if Path(database_path).absolute()==self.registry_path: raise ResearchError('JOB_REGISTRY_DATABASE_COLLISION')
        self.namespace=namespace; self.owner_id=text(owner_id)
        self.resolver=DatasetResolver(DatasetCatalog(self.root))
        self.journal=ResearchJournal(database_path); self.orchestrator=ResearchOrchestrator(self.journal,owner_id)
        self.ledger=ResearchTrialLedger(database_path); self._active_run_context=None
    def run(self,*,submission_id,definition,dataset_ref,split_policy_ref,cost_policy_ref,
            research_policy_ref=None,robustness_policy_ref=None,family_id=None,seed=None):
        self._active_run_context=None
        try:
            return self._run(submission_id=submission_id,definition=definition,dataset_ref=dataset_ref,split_policy_ref=split_policy_ref,
                cost_policy_ref=cost_policy_ref,research_policy_ref=research_policy_ref,robustness_policy_ref=robustness_policy_ref,family_id=family_id,seed=seed)
        except Exception as error:
            if self._active_run_context:
                family,run_id=self._active_run_context
                self.ledger.record_event(family,'RUN_FAILED',dict(run_id=run_id,reason_code=type(error).__name__))
            raise
    def _run(self,*,submission_id,definition,dataset_ref,split_policy_ref,cost_policy_ref,
             research_policy_ref,robustness_policy_ref,family_id,seed):
        text(submission_id)
        parsed=parse_strategy_definition(definition)
        if not isinstance(parsed,ParsedStrategyV02): raise ResearchError('EXPLICIT_V02_RESEARCH_PROFILE_REQUIRED')
        manifest=self.resolver.catalog.load(dataset_ref)
        if manifest.as_dict()['namespace']!=self.namespace: raise ResearchError('NAMESPACE_MISMATCH')
        split_policy=decode(read_local(self.root,split_policy_ref,65536))
        selected_cost=decode(read_local(self.root,cost_policy_ref,65536))
        selected=research_policy_ref is not None or robustness_policy_ref is not None
        if selected and (research_policy_ref is None or robustness_policy_ref is None or family_id is None or seed is None):
            raise ResearchError('COMPLETE_SELECTED_RESEARCH_BINDING_REQUIRED')
        if not selected and (family_id is not None or seed is not None): raise ResearchError('POLICY_REQUIRED_FOR_ADAPTIVE_RUN')
        selected_research=decode(read_local(self.root,research_policy_ref,65536)) if selected else None
        selected_robustness=decode(read_local(self.root,robustness_policy_ref,262144)) if selected else None
        if selected: text(family_id); research_integer(seed,0,(1<<64)-1)
        provenance=capture_provenance()
        inputs=dict(schema_version='r7-research-run-v0.2',namespace=self.namespace,submission_id=submission_id,
                    strategy=json.loads(parsed.canonical_json),dataset=manifest.as_dict(),
                    dataset_manifest_hash=manifest.manifest_hash,dataset_hash_verification='PENDING_AT_FREEZE',
                    split_policy=split_policy,split_policy_hash=digest(canonical(split_policy).encode()),
                    cost_policy=selected_cost,cost_policy_hash=digest(canonical(selected_cost).encode()),promotion_policy=None,
                    implementation_hash=provenance['implementation_hash'],provenance=provenance,random_seed=seed,
                    family_id=family_id,research_policy=selected_research,robustness_policy=selected_robustness,
                    random_algorithm='SHA256_COUNTER_REJECTION_V1' if selected else 'NOT_RUN',
                    information_cutoff=manifest.as_dict()['information_cutoff'])
        run_id='run-'+digest(canonical(inputs).encode())[7:]
        self.journal.register_run(run_id,inputs,now_utc())
        cached=self.journal.result(run_id,'diagnostic_report')
        if cached is not None: return self._outcome(cached)
        if selected:
            self.ledger.register_family(family_id,self.namespace,parsed.symbol,'TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
            self._active_run_context=(family_id,run_id)
            self.ledger.record_event(family_id,'RUN_STARTED',dict(run_id=run_id,strategy_hash=parsed.content_hash,input_hash=digest(canonical(inputs).encode())))
            self.ledger.record_event(family_id,'POLICY_SELECTION',dict(run_id=run_id,research_policy_hash=digest(canonical(selected_research).encode()),
                                                                     robustness_policy_hash=digest(canonical(selected_robustness).encode())))
        def admit(_):
            hardware=inspect_hardware(self.root)
            policy=ResourcePolicy.conservative(hardware.physical_memory_bytes)
            decision=policy.admission(available_memory_bytes=hardware.available_memory_bytes,
                                     disk_free_bytes=hardware.disk_free_bytes,disk_total_bytes=hardware.disk_total_bytes)
            if not decision.allowed: raise ResearchError(decision.reason_codes[0])
            return dict(hardware=hardware.to_dict(),memory_enforcement=policy.memory_enforcement,
                        memory_soft_budget_bytes=policy.memory_soft_budget_bytes)
        admission_stage=('resource_admission' if self.journal.result(run_id,'resource_admission') is None else
                         'resource_readmission:'+str(len(self.journal.attempts(run_id))))
        admission=self.orchestrator.execute(run_id,admission_stage,inputs,admit)
        context={}
        def resolve_plan(_):
            split=resolve_split_manifest(manifest,split_policy); context['split']=split
            if parsed.exit_policy['max_hold_seconds'] is None or parsed.exit_policy['max_hold_seconds']>split_policy['max_holding_seconds']:
                raise ResearchError('UNBOUNDED_OR_POLICY_EXCEEDING_HOLDING_HORIZON')
            return split.to_dict()
        split_result=self.orchestrator.execute(run_id,'split_resolution',inputs,resolve_plan)
        split=context.get('split') or resolve_split_manifest(manifest,split_policy)
        def resolve_dataset(_):
            dataset=self.resolver.resolve_development(dataset_ref,split.development.end); context['dataset']=dataset
            if parsed.symbol!=dataset.symbol or any(tf not in dataset.candles_by_timeframe for tf in parsed.required_timeframes): raise ResearchError('STRATEGY_DATASET_MISMATCH')
            return dict(manifest_hash=dataset.manifest_hash,logical_hash=dataset.logical_hash,container_hashes=list(dataset.container_hashes),
                        reason_codes=list(dataset.reason_codes),verification_scope=dataset.verification_scope,
                        row_counts={tf:len(rows) for tf,rows in dataset.candles_by_timeframe.items()})
        dataset_result=self.orchestrator.execute(run_id,'dataset_resolution',inputs,resolve_dataset)
        dataset=context.get('dataset') or self.resolver.resolve_development(dataset_ref,split.development.end)
        if dataset_result['manifest_hash']!=dataset.manifest_hash or dataset_result['logical_hash']!=dataset.logical_hash:
            raise ResearchError('DATASET_CHANGED_AFTER_FREEZE')
        cost=self.orchestrator.execute(run_id,'cost_resolution',inputs,lambda _:_cost_policy(selected_cost,self.namespace))
        if selected:
            def select_policies(_):
                research=ResearchPolicy.parse(selected_research).as_dict(); robust=parse_robustness_policy(selected_robustness)
                for policy in (research,robust):
                    if policy['namespace']!=self.namespace or policy['split_policy_hash']!=split.policy_hash or policy['cost_policy_hash']!=inputs['cost_policy_hash']:
                        raise ResearchError('RESEARCH_POLICY_BINDING_MISMATCH')
                return dict(research=research,robustness=robust)
            self.orchestrator.execute(run_id,'policy_resolution',inputs,select_policies)
        # Only the non-adaptive decoder holds the full validation input.
        # Compatibility and all adaptive execution ports discard sealed payloads.
        development_binding=DevelopmentBinding.from_dataset(dataset,split,cost) if dataset.funding_model is not None else None
        development_dataset=replace(dataset,candles_by_timeframe=development_binding.candles_by_timeframe,
                                    funding_model=development_binding.funding_model) if development_binding else dataset
        def compatible(_):
            if any(sum(row.close_time<=split.training.end for row in dataset.candles_by_timeframe[tf])>cost['max_evaluations']
                   for tf in parsed.required_timeframes): raise ResearchError('RESEARCH_EVALUATION_BUDGET_EXCEEDED')
            return execute_compatibility(json.loads(parsed.canonical_json),development_dataset,split.training,provenance)
        compatibility=self.orchestrator.execute(run_id,'compatibility',inputs,compatible)
        boundary=ExecutedCompatibilityBoundary(self.journal,run_id,parsed.content_hash)
        with open_sqlite_platform(self.registry_path,compatibility_boundary=boundary,research_namespace=self.namespace) as e6:
            outcome=e6.intake(json.loads(parsed.canonical_json),source_actor='R7_RESEARCH:'+self.namespace,
                              operation_id='research-intake:'+run_id)
            identity=StrategyIdentity(parsed.strategy_id,parsed.strategy_version)
            current=e6.get_strategy(identity)
            if compatibility['status']=='PASS' and current.current_lifecycle_state=='DRAFT':
                current=e6.begin_backtesting(identity,actor='R7_RESEARCH:'+self.namespace)
            reasons=list(dataset.reason_codes)
            if compatibility['status']!='PASS': reasons.extend(compatibility['reason_codes'])
            backtest=None; evidence_id=None
            if compatibility['status']=='PASS' and dataset.funding_model is not None:
                partition=split.development
                rows=tuple(row for row in dataset.candles_by_timeframe[parsed.evaluation_timeframe]
                           if partition.warmup_start<=row.open_time and row.close_time<=partition.end)
                def replay(claim):
                    if len(rows)>cost['max_evaluations']: raise ResearchError('RESEARCH_EVALUATION_BUDGET_EXCEEDED')
                    binding=project_e2_runtime_binding(runtime_profile='0.2.0',candles_by_timeframe=development_dataset.candles_by_timeframe,
                                                       availability_model=dataset.availability_model)
                    config=ReplayConfig(finite_decimal(cost['fixed_quantity']),cost['cost_model_version'],
                        FeeModel(cost['cost_model_version'],cost['maker_bps'],cost['taker_bps']),
                        SlippageModel(cost['cost_model_version'],cost['entry_bps'],cost['exit_bps']),development_dataset.funding_model,
                        run_created_at=now_utc(),scored_start=partition.start,scored_end=partition.end,
                        entry_start=partition.entry_start,entry_end=partition.entry_end)
                    with localcontext(REFERENCE_CONTEXT):
                        result=HistoricalReplayEngine(binding,config).run(parsed,rows,
                            DatasetDescriptor(dataset.dataset_id+':development:'+run_id,dataset.logical_hash,rows[0].open_time,rows[-1].close_time))
                    if capture_provenance()['implementation_hash']!=provenance['implementation_hash']: raise ResearchError('IMPLEMENTATION_CHANGED_DURING_REPLAY')
                    return result.to_contract(include_trades=True)
                backtest=self.orchestrator.execute(run_id,'development_replay',inputs,replay)
                def persist(_):
                    record=e6.record_backtest_result(backtest,verification_status='PASS',verification_kind='LOCAL_EXECUTION',
                        source_revision=provenance['implementation_hash'],environment=provenance['os']+'/'+provenance['python'],
                        command='E3 HistoricalReplayEngine.run/actual-E2-v0.2/development-only',result_ref='research:'+run_id+'/development_replay')
                    return dict(evidence_id=record.evidence_id)
                evidence_id=self.orchestrator.execute(run_id,'e6_backtest_persistence',dict(backtest_hash=digest(canonical(backtest).encode())),persist)['evidence_id']
            robustness=None; product=None; sealed_oos='NOT_RUN'; status='BLOCKED'; frozen=None
            if selected and backtest is not None:
                def robust_replay(claim):
                    def record_trial(event):
                        self.journal.renew(claim,now_utc(),lease_seconds=300)
                        self.ledger.record_event(family_id,'TRIAL',dict(run_id=run_id,
                            trial_id=run_id+':'+event['stage']+':'+event['variant_hash'],**event))
                    result=evaluate_robustness(json.loads(parsed.canonical_json),development_binding,selected_robustness,
                                              research_policy=selected_research,seed=seed,record_trial=record_trial).as_dict()
                    if capture_provenance()['implementation_hash']!=provenance['implementation_hash']: raise ResearchError('IMPLEMENTATION_CHANGED_DURING_REPLAY')
                    return result
                robustness=self.orchestrator.execute(run_id,'robustness',inputs,robust_replay)
                self.ledger._record_trials(family_id,run_id,robustness)
                status=robustness['status']; reasons.extend(robustness['reason_codes'])
                if robustness['status']=='PASS':
                    policies=dict(research=selected_research,robustness=selected_robustness,split=split_policy,cost=selected_cost)
                    frozen_result=self.orchestrator.execute(run_id,'finalist_freeze',inputs,
                        lambda _:self.ledger.freeze_finalist(run_id,parsed.content_hash,policies).as_dict())
                    frozen=self.ledger.freeze_finalist(run_id,parsed.content_hash,policies)
                    if frozen_result!=frozen.as_dict(): raise ResearchError('IMMUTABLE_FINALIST_CONFLICT')
                    product=self.orchestrator.execute(run_id,'sealed_oos',dict(finalist_hash=frozen.frozen_hash),
                        lambda _:evaluate_sealed_oos(frozen,SealedOOSBinding(self.ledger,self.resolver,dataset_ref)).as_dict())
                    status=product['status']; sealed_oos=status; reasons.extend(product['reason_codes'])
            else:
                if not selected: reasons.append('MISSING_PROMOTION_POLICY')
                reasons.extend(('ROBUSTNESS_NOT_RUN','SEALED_OOS_NOT_RUN'))
            report=dict(schema_version='r7-research-report-v0.2',run_id=run_id,namespace=self.namespace,status=status,
                        reason_codes=sorted(set(reasons)),compatibility=compatibility,backtest=backtest,
                        backtest_e6_evidence_id=evidence_id,strategy_lifecycle=current.current_lifecycle_state,
                        sealed_oos=sealed_oos,robustness=robustness,product_assessment=product,
                        frozen_finalist=None if frozen is None else frozen.as_dict(),
                        candidate_gate=dict(status='BLOCKED',reason_codes=['PRODUCT_LIFECYCLE_NOT_YET_QUALIFIED']),
                        provenance=provenance,inputs=inputs,dataset_resolution=dataset_result,
                        split_resolution=split_result,resource_admission=admission)
            report=self.orchestrator.execute(run_id,'diagnostic_report',inputs,lambda _:report)
            return self._outcome(report)
    def _outcome(self,report):
        return ResearchOutcome(report['run_id'],report['status'],tuple(report['reason_codes']),report['compatibility']['status'],report['strategy_lifecycle'])
    def report(self,run_id):
        result=self.journal.result(run_id,'diagnostic_report')
        if result is None: raise ResearchError('REPORT_NOT_READY')
        result['attempts']=self.journal.attempts(run_id)
        return result
    def close(self): self.ledger.close(); self.journal.close()
    def __enter__(self): return self
    def __exit__(self,*_): self.close()
