"""Retain a complete/provisional source qualification exactly, no status upgrade."""
from pathlib import Path
import hashlib,json,sys,re
from s09_ui_dependency_inputs import protected_bytes
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
revision=sys.argv[1];short=revision[:7]
source=BASE/f'r7-productization-S09-normal-fixture-qualified-{short}'
captured={'qualification.json':protected_bytes(source/'qualification.json',8*1024**2)}
report=json.loads(captured['qualification.json'])
target=REPO/f'status/codex/productization/S15/source-{short}'
assert not target.exists()
names=['qualification.json','qualification-context.json','hardware-observations.json']+[row['log'] for row in report['commands']]
assert len(names)==len(set(names))
for row in report['commands']:
    assert re.fullmatch(r'[0-9]{3}-phase_[12]-[a-z_]+\.log',row['log'])
    captured[row['log']]=protected_bytes(source/row['log'],8*1024**2)
    assert hashlib.sha256(captured[row['log']]).hexdigest()==row['log_sha256']
for name in names:
    if name not in captured:captured[name]=protected_bytes(source/name,8*1024**2)
target.mkdir(parents=True)
rows=[]
for name in names:
    assert Path(name).name==name
    raw=captured[name];published=raw.replace(b'\r\n',b'\n')
    with (target/name).open('xb') as stream:stream.write(published)
    row=dict(path=(target/name).relative_to(REPO).as_posix(),sha256='sha256:'+hashlib.sha256(published).hexdigest(),bytes=len(published),
             original_sha256='sha256:'+hashlib.sha256(raw).hexdigest(),publication='LF_NORMALIZED_TEXT;SEMANTICS_UNCHANGED')
    if published!=raw:
        raw_path=target/(name+'.raw')
        with raw_path.open('xb') as stream:stream.write(raw)
        row['raw_subject_path']=raw_path.relative_to(REPO).as_posix()
        rows.append(dict(path=row['raw_subject_path'],sha256=row['original_sha256'],bytes=len(raw),publication='EXACT_ORIGINAL_BYTES'))
    rows.append(row)
manifest=target.parent/f'source-artifact-hashes-{short}.json'
manifest.write_text(json.dumps(dict(executable_revision=revision,qualification_passed=report['passed'],artifacts=rows),indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(rows),passed=report['passed'])))
