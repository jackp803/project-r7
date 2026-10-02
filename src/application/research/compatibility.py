"""Executed E2 boundary. Context/results originate in trusted local composition."""
from datetime import timezone
import json

from application.datasets.catalog import canonical,digest,z
from application.research.evidence import capture_provenance,now_utc
from registry.models import CompatibilityEvidence,StrategyIdentity,EvidenceGateError
from strategy import StrategyRuntime,parse_strategy_definition
from strategy.v02.capabilities import build_capability_snapshot,check_compatibility,_revision
from strategy.v02.temporal import build_asof_bundle

def execute_compatibility(definition,dataset,partition,provenance):
    parsed=parse_strategy_definition(definition)
    snapshot=build_capability_snapshot()
    if snapshot.as_dict()['implementation_revision']!=provenance['implementation_hash']:
        raise EvidenceGateError('Implementation changed before compatibility execution')
    report=check_compatibility(json.loads(parsed.canonical_json),snapshot)
    gaps=[gap.reason for gap in report.gaps if gap.reason!='EXECUTION_NOT_QUALIFIED']
    boundary=partition.end
    bundle=build_asof_bundle({tf:rows for tf,rows in dataset.candles_by_timeframe.items() if tf in parsed.required_timeframes},
                             boundary,boundary,availability_model=dataset.availability_model)
    signal=StrategyRuntime().evaluate(parsed,bundle,boundary)
    healthy={'LONG_RULE_MATCHED','SHORT_RULE_MATCHED','NO_RULE_MATCHED','CONFLICTING_ENTRY_RULES'}
    gaps.extend(reason for reason in signal['reason_codes'] if reason not in healthy)
    if _revision()!=provenance['implementation_hash']: raise EvidenceGateError('Implementation changed during compatibility execution')
    return dict(status='BLOCKED' if gaps else 'PASS',reason_codes=sorted(set(gaps)),signal=signal,
                strategy_content_hash=parsed.content_hash,capability_snapshot_hash=snapshot.snapshot_hash,
                implementation_hash=provenance['implementation_hash'],dataset_manifest_hash=dataset.manifest_hash,
                checked_at=z(now_utc()),command='E2 StrategyRuntime.evaluate/explicit-v0.2/as-of-training',
                verification_kind='LOCAL_EXECUTION',provenance=provenance)

class ExecutedCompatibilityBoundary:
    """Private adapter consumes only a previously persisted actual E2 execution."""
    def __init__(self,journal,run_id,content_hash):
        self._journal,self._run_id,self._content_hash=journal,run_id,content_hash
    def check(self,definition):
        parsed=parse_strategy_definition(definition)
        result=self._journal.result(self._run_id,'compatibility')
        if not result or parsed.content_hash!=self._content_hash or result['strategy_content_hash']!=parsed.content_hash:
            raise EvidenceGateError('Missing or mismatched actual E2 execution')
        if result['implementation_hash']!=_revision(): raise EvidenceGateError('Stale E2 execution implementation')
        output_hash=digest(canonical(result).encode()); provenance=result['provenance']
        return CompatibilityEvidence('compat-'+output_hash[7:],StrategyIdentity(parsed.strategy_id,parsed.strategy_version),
                                     result['status'],'LOCAL_EXECUTION','E2:R7-v0.2-executed',result['checked_at'],
                                     tuple(result['reason_codes']),dict(strategy_content_hash=parsed.content_hash,
                                          capability_snapshot_hash=result['capability_snapshot_hash'],dataset_manifest_hash=result['dataset_manifest_hash']),
                                     source_revision=provenance['implementation_hash'],environment=provenance['os']+'/'+provenance['python'],
                                     command=result['command'],result_ref='research:'+self._run_id+'/compatibility/'+output_hash)
