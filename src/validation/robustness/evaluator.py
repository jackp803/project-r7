"""Actual E3/E2 development-only finite robustness execution."""
from dataclasses import dataclass,replace
from datetime import timedelta
from decimal import Decimal,localcontext
from itertools import product
import json
from types import MappingProxyType

from backtest.costs import FeeModel,SlippageModel
from backtest.e2_runtime import project_e2_runtime_binding
from backtest.metrics import calculate_metrics
from backtest.replay import DatasetDescriptor,HistoricalReplayEngine,ReplayConfig
from indicators.v02.common import REFERENCE_CONTEXT
from market_data.timeframes import timeframe_duration,is_timeframe_aligned
from strategy import compute_content_hash,parse_strategy_definition
from strategy.v02.models import ParsedStrategyV02
from .common import assessment,canonical,decimal,dec_text,digest,exact,fail,integer,utc,z
from .monte_carlo import evaluate_monte_carlo
from .policies import ResearchPolicy,assess_partition,parse_robustness_policy

@dataclass(frozen=True)
class ReplayWindow:
    start: object
    end: object
    warmup_start: object
    entry_start: object
    entry_end: object

@dataclass(frozen=True)
class DevelopmentBinding:
    candles_by_timeframe: object
    funding_model: object
    namespace: str
    availability_model: str
    dataset_id: str
    dataset_hash: str
    split_policy_hash: str
    cost_policy_json: str
    split_policy_json: str
    start: object
    end: object
    development: ReplayWindow
    @classmethod
    def from_dataset(cls,dataset,split,cost):
        # Discard the full owner object and every sealed row/event at the port.
        # Only hashes/clocks of the frozen full source remain as commitments.
        rows=MappingProxyType({tf:tuple(row for row in seq if row.close_time<=split.development.end)
                               for tf,seq in dataset.candles_by_timeframe.items()})
        if any(not seq for seq in rows.values()): fail('EMPTY_DEVELOPMENT_BINDING')
        if dataset.funding_model is None: fail('MISSING_FUNDING')
        if not hasattr(dataset.funding_model,'events'): fail('RECORDED_FUNDING_PROFILE_REQUIRED')
        funding=replace(dataset.funding_model,events=tuple((event,rate) for event,rate in dataset.funding_model.events
                                                         if event<split.development.end))
        part=split.development
        window=ReplayWindow(part.start,part.end,part.warmup_start,part.entry_start,part.entry_end)
        return cls(rows,funding,dataset.namespace,dataset.availability_model,dataset.dataset_id+':development-only',
                   dataset.logical_hash,split.policy_hash,canonical(cost),split.canonical_policy_json,dataset.start,part.end,window)
    def window(self,raw,*,embargo):
        exact(raw,('start','end')); start,end=utc(raw['start']),utc(raw['end']); p=json.loads(self.split_policy_json)
        if not self.start<=start<end<=self.end: fail('WALK_FORWARD_OUTSIDE_DEVELOPMENT')
        if any(not is_timeframe_aligned(value,tf) for tf in self.candles_by_timeframe for value in (start,end)): fail('MISALIGNED_WALK_FORWARD')
        horizon=max(p['max_holding_seconds'],p['label_horizon_seconds'])
        entry_start=start+timedelta(seconds=p['embargo_seconds'] if embargo else 0); entry_end=end-timedelta(seconds=horizon)
        if entry_start>=entry_end: fail('INSUFFICIENT_PURGED_WINDOW')
        warmup=max(timeframe_duration(tf)*p['warmup_bars'] for tf in self.candles_by_timeframe)
        return ReplayWindow(start,end,max(self.start,start-warmup),entry_start,entry_end)

@dataclass(frozen=True)
class _AdverseFunding:
    underlying: object
    multiplier: Decimal
    def cost(self,*args): return abs(self.underlying.cost(*args))*self.multiplier
    def assumptions(self):
        return dict(version='r7-adverse-recorded-funding-v1',underlying=self.underlying.assumptions(),
                    adverse_multiplier=dec_text(self.multiplier),mode='ABSOLUTE_RECORDED_COST_ALWAYS_CHARGED')

class _ReplayBudget:
    def __init__(self,policy): self.policy=policy; self.replays=0; self.evaluations=0
    def consume(self,count):
        if self.replays+1>self.policy['maximum_replays'] or self.evaluations+count>self.policy['maximum_evaluations']: fail('ROBUSTNESS_COMPUTATION_BUDGET_EXCEEDED')
        self.replays+=1; self.evaluations+=count

def _replay(definition,binding,window,budget,scenario=None):
    parsed=parse_strategy_definition(definition)
    if not isinstance(parsed,ParsedStrategyV02): fail('V02_ROBUSTNESS_SUBJECT_REQUIRED')
    if any(tf not in binding.candles_by_timeframe for tf in parsed.required_timeframes): fail('MISSING_REQUIRED_TIMEFRAME')
    split=json.loads(binding.split_policy_json)
    if parsed.exit_policy['max_hold_seconds'] is None or parsed.exit_policy['max_hold_seconds']>split['max_holding_seconds']: fail('UNBOUNDED_OR_POLICY_EXCEEDING_HOLDING_HORIZON')
    rows=tuple(row for row in binding.candles_by_timeframe[parsed.evaluation_timeframe]
               if window.warmup_start<=row.open_time and row.close_time<=window.end)
    if not rows: fail('EMPTY_REPLAY_WINDOW')
    budget.consume(len(rows)); cost=json.loads(binding.cost_policy_json)
    # Even a per-window E2 adapter cannot read a later evaluation window.
    visible={tf:tuple(row for row in seq if row.close_time<=window.end) for tf,seq in binding.candles_by_timeframe.items()}
    runtime=project_e2_runtime_binding(runtime_profile='0.2.0',candles_by_timeframe=visible,availability_model=binding.availability_model)
    fee_add=decimal(scenario['fee_add_bps']) if scenario else Decimal(0)
    entry_add=decimal(scenario['entry_slippage_add_bps']) if scenario else Decimal(0)
    exit_add=decimal(scenario['exit_slippage_add_bps']) if scenario else Decimal(0)
    funding=binding.funding_model if scenario is None else _AdverseFunding(binding.funding_model,decimal(scenario['funding_adverse_multiplier']))
    config=ReplayConfig(decimal(cost['fixed_quantity']),cost['cost_model_version'],
        FeeModel(cost['cost_model_version'],decimal(cost['maker_bps'])+fee_add,decimal(cost['taker_bps'])+fee_add),
        SlippageModel(cost['cost_model_version'],decimal(cost['entry_bps'])+entry_add,decimal(cost['exit_bps'])+exit_add),funding,
        run_created_at=binding.end,scored_start=window.start,scored_end=window.end,entry_start=window.entry_start,entry_end=window.entry_end)
    descriptor=DatasetDescriptor(binding.dataset_id+':'+digest([z(window.start),z(window.end)])[-16:],
                                 digest([binding.dataset_hash,z(window.warmup_start),z(window.end)]),rows[0].open_time,rows[-1].close_time)
    return HistoricalReplayEngine(runtime,config).run(parsed,rows,descriptor).to_contract(include_trades=True)

def _variants(subject,policy):
    parsed=parse_strategy_definition(subject)
    if not isinstance(parsed,ParsedStrategyV02): fail('V02_ROBUSTNESS_SUBJECT_REQUIRED')
    base=json.loads(parsed.canonical_json)
    referenced=set(); stack=[base['rules']]
    while stack:
        node=stack.pop()
        if isinstance(node,dict):
            if node.get('kind')=='parameter': referenced.add(node.get('name'))
            stack.extend(node.values())
        elif isinstance(node,list): stack.extend(node)
    for dim in policy['neighborhood']:
        name=dim['parameter']
        if name not in base['parameters'] or name not in referenced: fail('UNREFERENCED_NEIGHBORHOOD_PARAMETER')
        original=base['parameters'][name]
        if dim['type']=='INTEGER' and type(original) is not int or dim['type']=='DECIMAL' and not isinstance(original,str): fail('PARAMETER_TYPE_MISMATCH')
    result=[]
    for values in product(*(dim['values'] for dim in policy['neighborhood'])):
        raw=json.loads(parsed.canonical_json); changes=dict(zip((dim['parameter'] for dim in policy['neighborhood']),values))
        raw['parameters'].update(changes); raw['content_hash']=compute_content_hash(raw)
        variant=dict(variant_hash=raw['content_hash'],variant_id='variant-'+raw['content_hash'][7:],parameters=changes,status='PENDING',reason_codes=[])
        try: parse_strategy_definition(raw)
        except ValueError as error:
            variant.update(status='INVALID',reason_codes=[getattr(error,'code',type(error).__name__)])
        result.append((raw,variant))
    return base,result

def _evaluate_variant(raw,variant,binding,window,budget,research_policy,partition,*,recorder=None,stage='neighborhood'):
    v=json.loads(canonical(variant))
    def record(status,value):
        if recorder: recorder(dict(variant_hash=v['variant_hash'],stage=stage,status=status,reason_codes=value.get('reason_codes',[]),result_hash=digest(value)))
    if v['status']=='INVALID': record('INVALID',v); return v
    record('STARTED',v)
    try: backtest=_replay(raw,binding,window,budget)
    except Exception as error:
        record('FAILED',dict(reason_codes=[getattr(error,'code',type(error).__name__)])); raise
    decision=assess_partition(backtest,research_policy,partition)
    v.update(status=decision['status'],reason_codes=decision['reason_codes'],backtest=backtest,assessment=decision)
    record(v['status'],v)
    return v

def assess_walk_forward_aggregate(trades,research_policy):
    with localcontext(REFERENCE_CONTEXT):
        metrics=calculate_metrics(trades).to_contract_fields()
        return dict(metrics=metrics,assessment=assess_partition(metrics,research_policy,'walk_forward'))

def _walk_forward(variants,binding,policy,rp,budget,recorder):
    windows=[]; previous_end=None; previous_train_start=None
    # Validate the entire protocol before running any training/evaluation replay.
    for raw in policy['walk_forward_windows']:
        exact(raw,('training','evaluation')); train=binding.window(raw['training'],embargo=False); evaluation=binding.window(raw['evaluation'],embargo=True)
        if train.end>evaluation.start or previous_end and evaluation.start<previous_end or previous_train_start and train.start<previous_train_start: fail('OVERLAPPING_OR_UNORDERED_WALK_FORWARD')
        windows.append((train,evaluation)); previous_end=evaluation.end; previous_train_start=train.start
    result=[]; all_trades=[]; p=json.loads(binding.split_policy_json)
    for index,(train,evaluation) in enumerate(windows):
        candidates=[_evaluate_variant(raw,v,binding,train,budget,rp,'walk_forward',recorder=recorder,stage=f'walk_forward_training_{index}') for raw,v in variants]
        eligible=[v for v in candidates if v['status']=='PASS']
        chosen=sorted(eligible,key=lambda v:(-decimal(v['backtest']['net_pnl']),v['variant_hash']))[0] if eligible else None
        item=dict(training_start=z(train.start),training_end=z(train.end),evaluation_start=z(evaluation.start),evaluation_end=z(evaluation.end),
                  evaluation_entry_start=z(evaluation.entry_start),evaluation_entry_end=z(evaluation.entry_end),training_variants=candidates,
                  selected_variant_hash=None if chosen is None else chosen['variant_hash'],warmup='FEATURE_ONLY',boundary_overlap='PURGED',
                  purge_seconds=max(p['max_holding_seconds'],p['label_horizon_seconds']),embargo_seconds=p['embargo_seconds'],
                  status='BLOCKED',reason_codes=['NO_ADEQUATE_TRAINING_VARIANT'],evaluation=None)
        if chosen:
            definition=next(raw for raw,v in variants if v['variant_hash']==chosen['variant_hash'])
            backtest=_replay(definition,binding,evaluation,budget); decision=assess_partition(backtest,rp,'walk_forward')
            item.update(status=decision['status'],reason_codes=decision['reason_codes'],evaluation=backtest,assessment=decision)
            all_trades.extend(backtest['trades'])
        result.append(item)
    if len({trade['trade_id'] for trade in all_trades})!=len(all_trades): fail('DUPLICATE_WALK_FORWARD_TRADE')
    fraction=Decimal(sum(v['status']=='PASS' for v in result))/Decimal(len(result))
    blocked=any(v['status']=='BLOCKED' for v in result)
    aggregate=assess_walk_forward_aggregate(all_trades,rp); decision=aggregate['assessment']
    status='BLOCKED' if blocked or decision['status']=='BLOCKED' else 'PASS' if fraction>=decimal(policy['minimum_walk_forward_pass_fraction']) and decision['status']=='PASS' else 'FAIL'
    reasons=['INSUFFICIENT_EVIDENCE'] if blocked else []
    reasons+=decision['reason_codes']
    if fraction<decimal(policy['minimum_walk_forward_pass_fraction']): reasons.append('WALK_FORWARD_PASS_FRACTION_NOT_MET')
    return dict(status=status,windows=result,pass_fraction=dec_text(fraction),aggregate=aggregate['metrics'],aggregate_assessment=decision,
                scored_intervals_counted_once=True,reason_codes=sorted(set(reasons)))

def evaluate_robustness(subject,development_binding,policy,*,research_policy,seed,record_trial=None):
    if not isinstance(development_binding,DevelopmentBinding): fail('DEVELOPMENT_ONLY_BINDING_REQUIRED')
    integer(seed,0,(1<<64)-1); p=parse_robustness_policy(policy); b=development_binding
    if record_trial is not None and not callable(record_trial): fail('TRUSTED_TRIAL_RECORDER_REQUIRED')
    if research_policy is None:
        return assessment(dict(schema_version='r7-robustness-assessment-v0.2',status='BLOCKED',reason_codes=['MISSING_RESEARCH_POLICY'],
                               policy_hash=digest(p),seed=seed,stages='NOT_RUN'))
    rp=ResearchPolicy.parse(research_policy); r=rp.as_dict()
    for profile in (p,r):
        if profile['namespace']!=b.namespace or profile['split_policy_hash']!=b.split_policy_hash or profile['cost_policy_hash']!=digest(b.cost_policy_json.encode()): fail('RESEARCH_POLICY_BINDING_MISMATCH')
    for mc in p['monte_carlo']:
        if mc['drawdown_unit']!=r['drawdown_unit'] or decimal(mc['initial_equity'])!=decimal(r['initial_equity_usdt']): fail('MONTE_CARLO_UNIT_BINDING_MISMATCH')
    with localcontext(REFERENCE_CONTEXT):
        base,variants=_variants(subject,p); budget=_ReplayBudget(p)
        # Protocol validation is done before execution; windows never reach OOS.
        previous=None; previous_train=None; windows=[]
        for item in p['walk_forward_windows']:
            exact(item,('training','evaluation')); train=b.window(item['training'],embargo=False); evaluation=b.window(item['evaluation'],embargo=True)
            if train.end>evaluation.start or previous and evaluation.start<previous or previous_train and train.start<previous_train: fail('OVERLAPPING_OR_UNORDERED_WALK_FORWARD')
            windows.append((train,evaluation)); previous=evaluation.end; previous_train=train.start
        valid_count=sum(v['status']!='INVALID' for _,v in variants)
        planned=[b.development]*(1+valid_count+len(p['stress_scenarios']))
        for train,evaluation in windows: planned.extend([train]*valid_count+[evaluation])
        tf=parse_strategy_definition(base).evaluation_timeframe
        estimated=sum(sum(w.warmup_start<=row.open_time and row.close_time<=w.end for row in b.candles_by_timeframe[tf]) for w in planned)
        if len(planned)>p['maximum_replays'] or estimated>p['maximum_evaluations']: fail('ROBUSTNESS_COMPUTATION_BUDGET_EXCEEDED')
        development=_replay(base,b,b.development,budget); dev_assessment=assess_partition(development,rp,'development')
        neighbors=[_evaluate_variant(raw,v,b,b.development,budget,rp,'development',recorder=record_trial) for raw,v in variants]
        fraction=Decimal(sum(v['status']=='PASS' for v in neighbors))/Decimal(len(neighbors))
        neighborhood=dict(status='PASS' if fraction>=decimal(p['minimum_neighborhood_pass_fraction']) else 'FAIL',
                          variants=neighbors,pass_fraction=dec_text(fraction),denominator='ALL_DECLARED_VARIANTS_INCLUDING_INVALID')
        walk=_walk_forward(variants,b,p,rp,budget,record_trial); stress=[]
        for scenario in p['stress_scenarios']:
            backtest=_replay(base,b,b.development,budget,scenario)
            decision=assess_partition(backtest,rp,'development')
            if decimal(backtest['net_pnl'])<decimal(p['minimum_stress_net_pnl_usdt']) and decision['status']!='BLOCKED':
                decision.update(status='FAIL',reason_codes=decision['reason_codes']+['STRESS_TOLERANCE_NOT_MET'])
            stress.append(dict(scenario=scenario,status=decision['status'],reason_codes=decision['reason_codes'],backtest=backtest,
                               assumptions=['Explicit additional adverse fee/slippage in BPS',
                                            'Adverse funding always charges absolute recorded event cost']))
        samples=[trade['net_pnl'] for trade in development['trades']]
        mc=[evaluate_monte_carlo(samples,profile,seed=seed).as_dict() for profile in p['monte_carlo']]
        reasons=[]; blocked=False
        stages=[dev_assessment,neighborhood,walk,*stress,*mc]
        for stage in stages:
            if stage['status']=='BLOCKED': blocked=True; reasons.extend(stage.get('reason_codes',['INSUFFICIENT_EVIDENCE']))
        if neighborhood['status']=='FAIL': reasons.append('NEIGHBORHOOD_PASS_FRACTION_NOT_MET')
        reasons.extend(walk['reason_codes']); reasons.extend(dev_assessment['reason_codes'])
        if any(v['status']=='FAIL' for v in stress): reasons.append('STRESS_TOLERANCE_NOT_MET')
        for item in mc:
            if item['status']!='PASS': continue
            if decimal(item['drawdown_quantiles']['0.95'])>decimal(p['max_monte_carlo_drawdown_q95']): reasons.append('MONTE_CARLO_DRAWDOWN_LIMIT_EXCEEDED')
            if item['algorithm']=='MOVING_BLOCK_BOOTSTRAP' and decimal(item['expectancy_quantiles']['0.05'])<decimal(p['minimum_block_expectancy_q05_usdt_per_trade']): reasons.append('BLOCK_EXPECTANCY_SENSITIVITY_NOT_MET')
        raw_hashes=[digest(value) for value in [development,*[v['backtest'] for v in neighbors if 'backtest' in v],walk,*stress,*mc]]
        return assessment(dict(schema_version='r7-robustness-assessment-v0.2',status='BLOCKED' if blocked else 'FAIL' if reasons else 'PASS',
            reason_codes=sorted(set(reasons)),strategy_content_hash=base['content_hash'],namespace=b.namespace,dataset_hash=b.dataset_hash,
            development_end=z(b.end),policy=p,policy_hash=digest(p),research_policy=rp.as_dict(),research_policy_hash=rp.policy_hash,
            seed=seed,development=dict(backtest=development,assessment=dev_assessment),neighborhood=neighborhood,walk_forward=walk,
            stress=dict(scenarios=stress),monte_carlo=mc,raw_result_hashes=raw_hashes,
            budget=dict(replays=budget.replays,evaluations=budget.evaluations),selection_procedure=p['selection_procedure'],
            limitations=['Correlated development tests do not prove future profitability',
                         'Walk-forward selection is training-only; final OOS is unavailable through this binding',
                         'OHLC protective/time fills remain declared E3 conservative estimates']))
