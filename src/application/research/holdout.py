"""Append-only trial history, finalist freeze and one-shot sealed OOS access.

The application owns job authority; actual financial replay/assessment stays E3.
No canonical lifecycle state is stored here and no caller-supplied PASS is accepted.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
from decimal import localcontext

from application.datasets.resolver import DatasetResolver
from application.datasets.split_plan import resolve_split
from application.platform.resources import require_local_database_volume
from application.research.evidence import capture_provenance,now_utc,stamp
from indicators.v02.common import REFERENCE_CONTEXT
from validation.robustness.common import assessment,canonical,digest,exact,fail,freeze,hash_value,text,utc,z
from validation.robustness.evaluator import DevelopmentBinding,ReplayWindow,_ReplayBudget,_replay
from validation.robustness.product import assess_final_replay
from validation.robustness.policies import ResearchPolicy,parse_robustness_policy

@dataclass(frozen=True)
class FrozenFinalist:
    finalist_id: str
    canonical_json: str
    frozen_hash: str
    def as_dict(self): return json.loads(self.canonical_json)

class ResearchTrialLedger:
    def __init__(self,path):
        path=Path(path).absolute(); require_local_database_volume(path); path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self._db=sqlite3.connect(path,timeout=5); self._db.row_factory=sqlite3.Row
        self._db.execute('PRAGMA busy_timeout=5000'); self._db.execute('PRAGMA journal_mode=WAL'); self._db.execute('PRAGMA synchronous=FULL')
        migration=Path(__file__).resolve().parents[1]/'migrations/0003_research_trial_ledger.sql'
        self._db.executescript(migration.read_text(encoding='utf-8'))
    def register_family(self,family_id,namespace,symbol,selection_procedure):
        for value in (family_id,symbol): text(value)
        if namespace not in ('FIXTURE','LOCAL_RESEARCH') or selection_procedure!='TRAIN_NET_PNL_THEN_VARIANT_HASH_V1': fail('INVALID_EXPERIMENT_FAMILY')
        with self._db:
            self._db.execute('INSERT OR IGNORE INTO research_families VALUES(?,?,?,?,?)',(family_id,namespace,symbol,selection_procedure,stamp(now_utc())))
            row=self._family(family_id)
            if (row['namespace'],row['symbol'],row['selection_procedure'])!=(namespace,symbol,selection_procedure): fail('IMMUTABLE_EXPERIMENT_FAMILY_MISMATCH')
    def _family(self,family_id):
        row=self._db.execute('SELECT * FROM research_families WHERE family_id=?',(family_id,)).fetchone()
        if row is None: fail('UNKNOWN_EXPERIMENT_FAMILY')
        return dict(row)
    def record_event(self,family_id,kind,payload):
        self._family(family_id)
        if kind not in ('RUN_STARTED','TRIAL','RUN_FAILED','RUN_ABORTED','POLICY_SELECTION','MANUAL_CHAT_REVISION','FINALIST_FROZEN','ASSESSMENT_RECORDED'): fail('UNSUPPORTED_EXPERIMENT_EVENT')
        payload=freeze(payload); raw=canonical(payload); h=digest(raw.encode()); event_id=digest([family_id,kind,h])
        with self._db:
            self._db.execute('INSERT OR IGNORE INTO research_family_events VALUES(?,?,?,?,?,?)',(event_id,family_id,kind,raw,h,stamp(now_utc())))
        return event_id
    def events(self,family_id):
        self._family(family_id); results=[]
        for row in self._db.execute('SELECT rowid,* FROM research_family_events WHERE family_id=? ORDER BY rowid',(family_id,)).fetchall():
            value=dict(row)
            if digest(value['payload_json'].encode())!=value['payload_hash']: fail('LEDGER_EVENT_HASH_MISMATCH')
            value['payload']=json.loads(value.pop('payload_json')); results.append(value)
        return results
    def _run(self,run_id):
        try: row=self._db.execute('SELECT * FROM research_runs WHERE run_id=?',(run_id,)).fetchone()
        except sqlite3.OperationalError: fail('UNKNOWN_RESEARCH_RUN')
        if row is None: fail('UNKNOWN_RESEARCH_RUN')
        if digest(row['input_json'].encode())!=row['input_hash']: fail('RESEARCH_INPUT_HASH_MISMATCH')
        return json.loads(row['input_json']),row['input_hash']
    def _robustness(self,run_id):
        row=self._db.execute("SELECT * FROM research_attempts WHERE run_id=? AND stage='robustness' AND status='COMPLETE' ORDER BY attempt_id DESC LIMIT 1",(run_id,)).fetchone()
        if row is None: fail('ROBUSTNESS_NOT_COMPLETE')
        _,input_hash=self._run(run_id)
        if row['input_hash']!=input_hash: fail('ROBUSTNESS_INPUT_BINDING_MISMATCH')
        if digest(row['output_json'].encode())!=row['output_hash']: fail('ROBUSTNESS_OUTPUT_HASH_MISMATCH')
        return json.loads(row['output_json']),row['output_hash']
    def freeze_finalist(self,run,strategy_hash,policies):
        text(run); hash_value(strategy_hash); policies=freeze(policies)
        exact(policies,('research','robustness','split','cost'))
        inputs,input_hash=self._run(run); family=self._family(inputs['family_id']); robust,robust_hash=self._robustness(run)
        expected={'research':inputs['research_policy'],'robustness':inputs['robustness_policy'],'split':inputs['split_policy'],'cost':inputs['cost_policy']}
        if policies!=expected or inputs['strategy']['content_hash']!=strategy_hash: fail('FINALIST_INPUT_BINDING_MISMATCH')
        if robust['status']!='PASS': fail('ROBUSTNESS_NOT_PASS')
        if robust['research_policy_hash']!=ResearchPolicy.parse(policies['research']).policy_hash or robust['policy_hash']!=digest(parse_robustness_policy(policies['robustness'])):
            fail('ROBUSTNESS_SELECTED_POLICY_MISMATCH')
        if robust['strategy_content_hash']!=strategy_hash or robust['namespace']!=family['namespace']: fail('ROBUSTNESS_SUBJECT_MISMATCH')
        if inputs['namespace']!=family['namespace'] or inputs['strategy']['symbol']!=family['symbol']: fail('EXPERIMENT_FAMILY_SUBJECT_MISMATCH')
        provenance=inputs['provenance']
        if capture_provenance()['implementation_hash']!=provenance['implementation_hash']: fail('IMPLEMENTATION_CHANGED_BEFORE_FINALIST')
        for key,source in (('research_policy_hash','research'),('policy_hash','robustness')):
            # The evaluator canonicalizes finite decimals; verify against its
            # actual selected policy, retaining the originally frozen bytes too.
            if robust[key]!=digest(robust['research_policy'] if source=='research' else robust['policy']): fail('ROBUSTNESS_POLICY_HASH_MISMATCH')
        existing=self._db.execute('SELECT * FROM research_finalists WHERE run_id=?',(run,)).fetchone()
        if existing:
            frozen=FrozenFinalist(existing['finalist_id'],existing['frozen_json'],existing['frozen_hash']); self.verify_finalist(frozen); return frozen
        frozen_at=stamp(now_utc()); finalist_id='finalist-'+digest([run,input_hash,robust_hash])[7:]
        document=dict(schema_version='r7-frozen-finalist-v0.2',finalist_id=finalist_id,run_id=run,family_id=inputs['family_id'],
                      namespace=family['namespace'],symbol=family['symbol'],strategy=inputs['strategy'],strategy_content_hash=strategy_hash,
                      policies=policies,policy_hashes={k:digest(v) for k,v in policies.items()},split_policy_hash=digest(policies['split']),
                      dataset_manifest_hash=inputs['dataset_manifest_hash'],robustness_hash=robust_hash,run_input_hash=input_hash,
                      provenance=provenance,random_seed=inputs['random_seed'],frozen_at=frozen_at)
        raw=canonical(document); frozen_hash=digest(raw.encode())
        with self._db:
            self._db.execute('INSERT OR IGNORE INTO research_finalists VALUES(?,?,?,?,?,?)',(finalist_id,run,inputs['family_id'],raw,frozen_hash,frozen_at))
        row=self._db.execute('SELECT * FROM research_finalists WHERE run_id=?',(run,)).fetchone()
        frozen=FrozenFinalist(row['finalist_id'],row['frozen_json'],row['frozen_hash'])
        self._record_trials(inputs['family_id'],run,robust)
        self.record_event(inputs['family_id'],'FINALIST_FROZEN',dict(run_id=run,finalist_id=frozen.finalist_id,frozen_hash=frozen.frozen_hash))
        return frozen
    def _record_trials(self,family_id,run_id,robustness):
        variants=[('neighborhood',v) for v in robustness['neighborhood']['variants']]
        for index,window in enumerate(robustness['walk_forward']['windows']):
            variants.extend((f'walk_forward_training_{index}',v) for v in window['training_variants'])
        for stage,variant in variants:
            self.record_event(family_id,'TRIAL',dict(run_id=run_id,trial_id=run_id+':'+stage+':'+variant['variant_hash'],
                variant_hash=variant['variant_hash'],stage=stage,status=variant['status'],reason_codes=variant['reason_codes'],
                result_hash=digest(variant)))
    def verify_finalist(self,finalist):
        if not isinstance(finalist,FrozenFinalist): fail('TRUSTED_FROZEN_FINALIST_REQUIRED')
        row=self._db.execute('SELECT * FROM research_finalists WHERE finalist_id=?',(finalist.finalist_id,)).fetchone()
        if row is None or finalist.canonical_json!=row['frozen_json'] or finalist.frozen_hash!=row['frozen_hash'] or digest(row['frozen_json'].encode())!=row['frozen_hash']: fail('FINALIST_PROVENANCE_MISMATCH')
        return finalist.as_dict()
    def observe_holdout(self,family_id,start,end,*,kind,reference_hash):
        family=self._family(family_id); lower,upper=utc(start),utc(end); hash_value(reference_hash)
        if lower>=upper or kind not in ('CHAT_OBSERVATION','MANUAL_OBSERVATION','EXTERNAL_REPORTED_OBSERVATION'): fail('INVALID_HOLDOUT_OBSERVATION')
        identity=digest([family_id,z(lower),z(upper),kind,reference_hash])
        with self._db:
            self._db.execute('INSERT OR IGNORE INTO research_holdout_observations VALUES(?,?,?,?,?,?,?,?,?,?)',
                (identity,None,family_id,family['namespace'],family['symbol'],z(lower),z(upper),kind,reference_hash,stamp(now_utc())))
        return identity
    def claim_holdout(self,finalist):
        value=self.verify_finalist(finalist); period=value['policies']['split']['sealed_oos']
        lower,upper=utc(period['start']),utc(period['end'])
        if lower>=upper: fail('INVALID_HOLDOUT_PERIOD')
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            rows=self._db.execute('SELECT * FROM research_holdout_observations WHERE namespace=? AND symbol=?',
                                 (value['namespace'],value['symbol'])).fetchall()
            # Parse clocks, not string ordering: fractional RFC3339 timestamps
            # must not permit a period to escape overlap detection.
            overlaps=[row for row in rows if utc(row['start_at'])<upper and lower<utc(row['end_at'])]
            if overlaps:
                own=any(row['finalist_id']==finalist.finalist_id for row in overlaps)
                return dict(allowed=False,reason_code='HOLDOUT_EXPOSED_INCOMPLETE' if own else 'HOLDOUT_ALREADY_OBSERVED')
            observation_id=digest([finalist.finalist_id,'EVALUATION_BEGIN'])
            self._db.execute('INSERT INTO research_holdout_observations VALUES(?,?,?,?,?,?,?,?,?,?)',
                (observation_id,finalist.finalist_id,value['family_id'],value['namespace'],value['symbol'],z(lower),z(upper),
                 'EVALUATION_BEGIN',finalist.frozen_hash,stamp(now_utc())))
            return dict(allowed=True,observation_id=observation_id)
    def holdout_observations(self):
        return [dict(row) for row in self._db.execute('SELECT rowid,* FROM research_holdout_observations ORDER BY rowid').fetchall()]
    def result(self,finalist):
        self.verify_finalist(finalist)
        row=self._db.execute('SELECT * FROM research_holdout_results WHERE finalist_id=?',(finalist.finalist_id,)).fetchone()
        if row is None: return None
        if digest(row['result_json'].encode())!=row['result_hash']: fail('HOLDOUT_RESULT_HASH_MISMATCH')
        return assessment(json.loads(row['result_json']))
    def _persist_result(self,finalist,result):
        self.verify_finalist(finalist)
        if len(result.canonical_json.encode())>8*1024*1024: fail('HOLDOUT_RESULT_SIZE_LIMIT')
        with self._db:
            self._db.execute('INSERT OR IGNORE INTO research_holdout_results VALUES(?,?,?,?)',
                (finalist.finalist_id,result.canonical_json,result.assessment_hash,stamp(now_utc())))
            row=self._db.execute('SELECT result_hash FROM research_holdout_results WHERE finalist_id=?',(finalist.finalist_id,)).fetchone()
            if row['result_hash']!=result.assessment_hash: fail('IMMUTABLE_HOLDOUT_RESULT_CONFLICT')
        value=finalist.as_dict()
        self.record_event(value['family_id'],'ASSESSMENT_RECORDED',dict(finalist_id=finalist.finalist_id,
                          status=result.as_dict()['status'],result_hash=result.assessment_hash))
        return result
    def close(self): self._db.close()
    def __enter__(self): return self
    def __exit__(self,*_): self.close()

class SealedOOSBinding:
    """Opaque local reference, not an author-provided payload/callback/decision."""
    def __init__(self,ledger,resolver,dataset_ref):
        if not isinstance(ledger,ResearchTrialLedger) or not isinstance(resolver,DatasetResolver): fail('TRUSTED_HOLDOUT_COMPOSITION_REQUIRED')
        self._ledger=ledger; self._resolver=resolver; self._dataset_ref=text(dataset_ref)
    def _replay_final(self,value):
        if capture_provenance()['implementation_hash']!=value['provenance']['implementation_hash']: fail('IMPLEMENTATION_CHANGED_BEFORE_OOS')
        manifest=self._resolver.catalog.load(self._dataset_ref)
        if manifest.manifest_hash!=value['dataset_manifest_hash']: fail('HOLDOUT_DATASET_CHANGED_AFTER_FREEZE')
        dataset=self._resolver.resolve(self._dataset_ref); split=resolve_split(dataset,value['policies']['split'])
        if split.policy_hash!=value['split_policy_hash'] or dataset.namespace!=value['namespace'] or dataset.symbol!=value['symbol']: fail('HOLDOUT_BINDING_MISMATCH')
        if dataset.funding_model is None: fail('MISSING_FUNDING')
        part=split.sealed_oos
        window=ReplayWindow(part.start,part.end,part.warmup_start,part.entry_start,part.entry_end)
        # Created only after the durable read claim. Never given to adaptive code.
        replay_binding=DevelopmentBinding(dataset.candles_by_timeframe,dataset.funding_model,dataset.namespace,
            dataset.availability_model,dataset.dataset_id+':sealed-oos',dataset.logical_hash,split.policy_hash,
            canonical(value['policies']['cost']),split.canonical_policy_json,dataset.start,part.end,window)
        budget=_ReplayBudget({'maximum_replays':1,'maximum_evaluations':value['policies']['cost']['max_evaluations']})
        with localcontext(REFERENCE_CONTEXT): result=_replay(value['strategy'],replay_binding,window,budget)
        if capture_provenance()['implementation_hash']!=value['provenance']['implementation_hash']: fail('IMPLEMENTATION_CHANGED_DURING_OOS')
        return dict(backtest=result,dataset_verification=dict(scope=dataset.verification_scope,manifest_hash=dataset.manifest_hash,
                    logical_hash=dataset.logical_hash,container_hashes=list(dataset.container_hashes),
                    row_counts={tf:len(rows) for tf,rows in dataset.candles_by_timeframe.items()}))

def evaluate_sealed_oos(finalist,holdout_binding):
    if not isinstance(holdout_binding,SealedOOSBinding): fail('OPAQUE_SEALED_OOS_BINDING_REQUIRED')
    ledger=holdout_binding._ledger; value=ledger.verify_finalist(finalist)
    cached=ledger.result(finalist)
    if cached is not None: return cached
    claim=ledger.claim_holdout(finalist)
    if not claim['allowed']:
        blocked=assessment(dict(schema_version='r7-product-assessment-v0.2',status='BLOCKED',
            reason_codes=[claim['reason_code']],finalist_id=finalist.finalist_id,run_id=value['run_id'],
            namespace=value['namespace'],strategy_content_hash=value['strategy_content_hash'],independent_oos=False,
            sealed_backtest=None,canonical_oos_decision=None,raw_result_hashes=[],provenance=value['provenance']))
        # A competing reader has no publication authority over the first owner.
        # After a crash this remains incomplete, never permission to replay.
        return blocked if claim['reason_code']=='HOLDOUT_EXPOSED_INCOMPLETE' else ledger._persist_result(finalist,blocked)
    replay=holdout_binding._replay_final(value); robust,_=ledger._robustness(value['run_id'])
    trials=len({event['payload']['trial_id'] for event in ledger.events(value['family_id']) if event['kind']=='TRIAL'})
    result=assess_final_replay(finalist=value,robustness=robust,backtest=replay['backtest'],
                             source_verification=replay['dataset_verification'],trial_count=trials)
    return ledger._persist_result(finalist,result)
