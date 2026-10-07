"""Preserve reviewed draft history and narrow two assertion descriptions."""
from pathlib import Path
import json,hashlib
base=Path(__file__).resolve().parent
expected={
 'S15-cloud-support-selection-fec8af0.json':'64d93c4c9529e5bd448c146d447949b8b72f81d6bdb1637cabec99f8dcc9d922',
 'S15-cloud-support-draft-fec8af0.json':'4d82f106da70a8d1e3eb7af237a477de749224297408695bfd17c7eef180cb14'}
for name,value in expected.items():
    path=base/name;raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==value
    history=base/(path.stem+'.before-cloud-wording-review.json');assert not history.exists();history.write_bytes(raw)
path=base/'S15-cloud-support-selection-fec8af0.json';body=json.loads(path.read_bytes())
row=next(row for row in body['requirements'] if row['id']=='CLOUD-03')
assert 'target remains intact' in row['supported_behavior']
row['supported_behavior']=row['supported_behavior'].replace('target remains intact','target file still exists')
row=next(row for row in body['requirements'] if row['id']=='CLOUD-09')
assert 'opt-in values preserve exact strings' in row['supported_behavior']
row['supported_behavior']=row['supported_behavior'].replace('opt-in values preserve exact strings',"opt-in net_pnl matches the owner's exact string")
path.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
(base/'S15-cloud-support-draft-fec8af0.json').unlink()
print('Preserved both history bytes; narrowed two cloud descriptions before fresh regeneration.')
