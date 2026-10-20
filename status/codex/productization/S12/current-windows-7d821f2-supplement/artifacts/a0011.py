"""Correct advisory CLOUD10 interpretation only; preserve prior drafts, no PASS."""
from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
bindings=[]
for name in ('acceptance-cloud-trade-expanded-map.json','final-acceptance-record-plan.json','POSTCHECKPOINT_LOCAL_MASTER_CHECKLIST.json'):
    path=base/name;raw=path.read_bytes();value=json.loads(raw)
    backup=base/('cloud10-before-correction-'+name)
    with backup.open('xb') as stream:stream.write(raw)
    def update(item):
        if isinstance(item,dict):
            if item.get('requirement_id')=='CLOUD-10':
                if 'concrete_uncovered_clauses_or_scope_limits' in item:
                    item['concrete_uncovered_clauses_or_scope_limits']=[
                        'Actual shipped4h EMA/ADX/ATR and4h-direction/15mDonchian examples need exact coverage; current4h is EMA-only and MTF1h/4h.',
                        'Ship unsupported-feature input and its actual typed capability-gap receipt; in-memory constructor negative alone does not establish that deliverable.',
                        'Tactical authoring does not itself establish runtime expiry/protection; use separate temporal/PAPER evidence. No authored market-data-gap scenario is required.']
                if 'uncovered_or_conditional_clauses' in item:
                    item['uncovered_or_conditional_clauses']=[
                        'Exact4h EMA/ADX/ATR and4h-direction/15mDonchian authored examples, plus shipped unsupported-feature input/actual typed capability-gap receipt, need coverage. Runtime tactical expiry remains separately mapped. No market-data-gap authoring requirement.']
                item['interpretation_correction_ref']='artifacts/current-windows-20261019/cloud10-authoritative-clause-clarification.json'
            if item.get('row')=='CLOUD-10':
                item['gap']='Exact4h EMA/ADX/ATR and4h/15mDonchian examples plus shipped unsupported-feature input/actual typed capability-gap receipt. Gap means unsupported capability, not market-data gaps. Runtime expiry is separate PQR scope.'
            for child in item.values():update(child)
        elif isinstance(item,list):
            for child in item:update(child)
    update(value)
    safe=(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
    path.write_bytes(safe)
    bindings.append(dict(ref=name,previous_hash=sha(raw),corrected_hash=sha(safe),previous_ref=backup.name))
report=dict(scope='ADVISORY_INTERPRETATION_CORRECTION_ONLY',execution='NO_SOURCE_OR_NATIVE_EXECUTION',
    acceptance_credit='NONE',clarification_hash=sha((base/'cloud10-authoritative-clause-clarification.json').read_bytes()),files=bindings)
with (base/'cloud10-map-correction-execution.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(corrected_drafts=len(bindings),acceptance_credit='NONE')))
