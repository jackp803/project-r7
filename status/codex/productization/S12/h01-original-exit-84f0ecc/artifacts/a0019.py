from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
recipe=json.loads((BASE/'h01-original-exit-positive-draft-recipe-20261020.json').read_bytes())
for row in recipe['source_hashes']:
    assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
prepared=[]
for row in recipe['drafts']:
    raw=(BASE/row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
    target=ROOT/'tests/product'/row['path'].removesuffix('.unapplied');assert not target.exists()
    text=raw.decode('utf-8').replace('UNAPPLIED / NOT_EXECUTED. ','').replace('UNAPPLIED / NOT_EXECUTED: ','')
    prepared.append((target,text))
for target,text in prepared:target.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(applied=len(prepared),status='APPLIED_NOT_EXECUTED')))
