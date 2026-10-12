"""Explicit public native intake/build corpus; no private profile traversal."""
import hashlib,json,sys
from pathlib import Path
from s09_ui_dependency_inputs import protected_bytes
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
source=sys.argv[1];short=source[:7];S15=REPO/'status/codex/productization/S15'
local=BASE/f'r7-native-S15-negative-intake-{short}';target=S15/f'native-negative-intake-{short}'
assert not target.exists()
names=['preparation.json','inputs.json','outcome.json','expired-authoring-input.json','observed-native-tty-enrollment.json','observed-native-tty-enrollment.log',
    '01-init.log','02-prepare-fixture.log','03-configure-research.log','author-partial.log','author-malformed.log',
    'author-unsupported.log','author-expired.log','browser-initial.log','browser-partial-recovered.log','browser-conflict.log',
    'control-negative-intake.log','initial.png','partial-recovered.png','conflict.png']
files=[(local/name,target/name) for name in names]
for name in ['s15_native_negative_intake_v2.py','s15_native_negative_intake_browser_v2.mjs','record_s15_native_negative_tty.py',
    's15_negative_intake_native_build.py','retain_s15_negative_intake_v2.py','retain_s15_source_attempt.py',
    'publish_s15_negative_checkpoint.py']:
    files.append((BASE/name,target/'harness'/name))
native=BASE/f'r7-native-windows-S15-negative-intake-{short}'
files.extend([(BASE/f'S15-negative-intake-{short}-native-build.json',S15/f'native-build-{short}.json'),
    (BASE/f'S15-negative-intake-{short}-native-build.log',S15/f'native-build-{short}.log'),
    (native/'build-result.json',target/'build-result.json'),
    (native/'dist/R7/distribution.json',target/'distribution.json'),
    (native/'dist/R7/licenses/inventory.json',target/'license-inventory.json')])
rows=[]
captured={path:protected_bytes(path,8*1024**2) for path,_ in files}
target.mkdir(parents=True)
for path,destination in files:
    raw=captured[path];destination.parent.mkdir(exist_ok=True)
    published=raw.replace(b'\r\n',b'\n') if path.suffix in ('.json','.log','.py','.mjs') else raw
    with destination.open('xb') as stream:stream.write(published)
    rows.append(dict(path=destination.relative_to(REPO).as_posix(),sha256='sha256:'+hashlib.sha256(published).hexdigest(),
        original_sha256='sha256:'+hashlib.sha256(raw).hexdigest(),bytes=len(published)))
    if published!=raw:
        original=destination.with_name(destination.name+'.raw')
        with original.open('xb') as stream:stream.write(raw)
        rows[-1]['raw_subject_path']=original.relative_to(REPO).as_posix()
        rows.append(dict(path=original.relative_to(REPO).as_posix(),sha256='sha256:'+hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
(S15/f'native-negative-intake-artifact-hashes-{short}.json').write_text(json.dumps(dict(source_revision=source,
    scope='EXPLICIT_SANITIZED_PUBLIC_ALLOWLIST;PRIVATE_FIXTURE_EXCLUDED',artifacts=rows),indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(rows),source_revision=source)))
