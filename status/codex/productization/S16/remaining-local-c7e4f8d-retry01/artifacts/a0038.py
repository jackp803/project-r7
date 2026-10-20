"""Normalize only retained derivative line-end whitespace; originals unchanged."""
from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
folder=ROOT/'status/codex/productization/S16'
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
changes={}
for name in ('remaining-local-c7e4f8d','remaining-local-c7e4f8d-retry01'):
    changed=[]
    for path in sorted((folder/name/'artifacts').glob('*')):
        if path.suffix=='.png':continue
        raw=path.read_bytes();safe=('\n'.join(line.rstrip() for line in raw.decode('utf-8').splitlines()).rstrip()+'\n').encode()
        if raw!=safe:
            changed.append(dict(ref=path.relative_to(folder/name).as_posix(),before=digest(raw),after=digest(safe)))
            path.write_bytes(safe)
    changes[name]=changed
first=folder/'remaining-local-c7e4f8d/failure.json'
v=json.loads(first.read_bytes());v['retained_derivative_whitespace_normalization']=changes['remaining-local-c7e4f8d']
first.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
manifest=folder/'remaining-local-c7e4f8d-retry01/disposition.json';v=json.loads(manifest.read_bytes())
for change in changes['remaining-local-c7e4f8d-retry01']:
    item=next(row for row in v['artifacts'] if row['retained_ref']==change['ref'])
    if item['retained_hash']!=change['before']:raise ValueError('Previous retained hash mismatch')
    item.update(retained_hash=change['after'],normalization=item['normalization']+';TRAILING_LINE_WHITESPACE_REMOVED',
        before_whitespace_normalization_hash=change['before'])
ref='artifacts/a0038.py';raw=Path(__file__).read_bytes();(manifest.parent/ref).write_bytes(raw)
v['artifacts'].append(dict(original_ref=Path(__file__).name,retained_ref=ref,original_hash=digest(raw),
    retained_hash=digest(raw),normalization='NONE'))
for item in v['artifacts']:
    if digest((manifest.parent/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained readback mismatch')
manifest.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(changed_derivatives=sum(map(len,changes.values())),verified_retained=len(v['artifacts']),original_logs='UNCHANGED')))
