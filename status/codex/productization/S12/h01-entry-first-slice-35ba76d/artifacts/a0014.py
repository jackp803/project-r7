from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
recipe=json.loads((BASE/'h01-entry-negative-tests-recipe-20261020.json').read_bytes())
recovery=json.loads((BASE/'h01-entry-recovery-schema-drafts-20261020.json').read_bytes())
drafts=[(d['path'],'tests/product/'+d['path'].removesuffix('.unapplied'),d['sha256']) for d in recipe['drafts']]
drafts += [(d['ref'],d['intended_path'],d['sha256']) for d in recovery['artifacts']]
prepared=[]
for ref,target,wanted in drafts:
    raw=(BASE/ref).read_bytes();assert hashlib.sha256(raw).hexdigest()==wanted
    path=ROOT/target;assert not path.exists()
    data=raw.decode('utf-8').replace('UNAPPLIED / NOT_EXECUTED. ','').replace('Intended: tests/product/h01_entry_recovery_fixture.py. No acceptance credit.','Controlled FIXTURE source regression; separate from native acceptance.')
    prepared.append((ref,target,wanted,data))
for ref,target,wanted,data in prepared:
    (ROOT/target).write_text(data,encoding='utf-8',newline='\n')
report=dict(status='APPLIED_NOT_EXECUTED',source_context='Root reviewed current H01 plus drafts; only geometry and intrinsic lineage validation changed since drafts, interfaces unchanged.',applied=[dict(original_ref=ref,original_sha256=wanted,path=target,applied_sha256=hashlib.sha256((ROOT/target).read_bytes()).hexdigest()) for ref,target,wanted,_ in prepared])
(BASE/'h01-entry-tests-root-application-20261020.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(applied=len(prepared))))
