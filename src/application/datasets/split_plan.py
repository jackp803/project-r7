from dataclasses import dataclass
from datetime import timedelta

from application.datasets.catalog import canonical,digest,exact,fail,positive_int,text,utc
from market_data.timeframes import is_timeframe_aligned,timeframe_duration

@dataclass(frozen=True)
class SplitPartition:
    name: str
    start: object
    end: object
    warmup_start: object
    entry_start: object
    entry_end: object
    sealed: bool

@dataclass(frozen=True)
class FrozenSplitPlan:
    training: SplitPartition
    development: SplitPartition
    sealed_oos: SplitPartition
    dataset_manifest_hash: str
    policy_hash: str
    canonical_policy_json: str
    namespace: str
    def to_dict(self):
        from dataclasses import asdict
        from application.datasets.catalog import z
        return dict(schema_version='r7-frozen-split-plan-v0.2',dataset_manifest_hash=self.dataset_manifest_hash,
                    policy_hash=self.policy_hash,namespace=self.namespace,
                    partitions={name:{key:z(value) if hasattr(value,'isoformat') else value
                                      for key,value in asdict(getattr(self,name)).items()}
                                for name in ('training','development','sealed_oos')})

def resolve_split(dataset,policy):
    return _resolve_split(dataset.namespace,dataset.manifest_hash,dataset.start,dataset.end,tuple(dataset.candles_by_timeframe),policy)

def resolve_split_manifest(manifest,policy):
    """Freeze clocks from a strict manifest before any sealed prices are decoded."""
    value=manifest.as_dict(); containers=value['candles']
    return _resolve_split(value['namespace'],manifest.manifest_hash,max(utc(c['start']) for c in containers),
                          min(utc(c['end']) for c in containers),tuple(c['timeframe'] for c in containers),policy)

def _resolve_split(namespace,manifest_hash,dataset_start,dataset_end,timeframes,policy):
    # Freeze before validation/use so subsequent caller mutation cannot revise it.
    import json
    try: policy=json.loads(canonical(policy))
    except (ValueError,TypeError,RecursionError): fail('INVALID_SPLIT_POLICY')
    exact(policy,('schema_version','policy_id','generation','namespace','training','development','sealed_oos',
                  'warmup_bars','max_holding_seconds','label_horizon_seconds','embargo_seconds','embargo_rationale'))
    if policy['schema_version']!='r7-split-policy-v0.2' or policy['namespace']!=namespace: fail('INVALID_SPLIT_PROFILE')
    text(policy['policy_id']); positive_int(policy['generation'],2147483647)
    warmup=positive_int(policy['warmup_bars'],100000)
    hold=positive_int(policy['max_holding_seconds'],31536000); label=positive_int(policy['label_horizon_seconds'],31536000)
    embargo=positive_int(policy['embargo_seconds'],31536000); text(policy['embargo_rationale'])
    horizon=max(hold,label); partitions=[]; previous_end=None
    warmup_duration=max(timeframe_duration(tf)*warmup for tf in timeframes)
    for name in ('training','development','sealed_oos'):
        item=policy[name]; exact(item,('start','end')); start,end=utc(item['start']),utc(item['end'])
        if start>=end or start<dataset_start or end>dataset_end or (previous_end and start<previous_end): fail('INVALID_SPLIT_RANGE')
        if any(not is_timeframe_aligned(value,tf) for tf in timeframes for value in (start,end)): fail('MISALIGNED_SPLIT')
        entry_start=start+(timedelta(seconds=embargo) if previous_end else timedelta(0))
        entry_end=end-timedelta(seconds=horizon)
        if entry_start>=entry_end: fail('INSUFFICIENT_PURGED_PARTITION')
        partitions.append(SplitPartition(name,start,end,max(dataset_start,start-warmup_duration),entry_start,entry_end,name=='sealed_oos'))
        previous_end=end
    raw=canonical(policy)
    return FrozenSplitPlan(*partitions,manifest_hash,digest(raw.encode()),raw,policy['namespace'])
