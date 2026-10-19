"""Historical scoped evidence only, after all guarded checkpoint runs end."""
from pathlib import Path
import hashlib,json,re,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.qualification import _sanitize
from application.paper.qualification import artifact_bytes
from application.paper.inventory import NATIVE_ASSERTIONS,current_target
from application.cloud.manifest import safe_component,safe_relative
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
revision=sys.argv[1]
if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Exact historical revision required')
stage=BASE/('native07-depth-'+revision[:7]+'-first');captured={}
def capture(path,expected=None):
    path=Path(path)
    for part in path.relative_to(PROJECT).parts:safe_component(part)
    raw=artifact_bytes(path.parent,path.name)
    if expected is not None and sha(raw)!=expected:raise ValueError('Historical artifact changed')
    if path in captured and captured[path]!=raw:raise ValueError('Historical snapshot differs')
    captured[path]=raw;return raw
checkpoint=json.loads(capture(stage/'checkpoint.json'))
passed=checkpoint.get('passed') is True
if (checkpoint.get('revision')!=revision
        or checkpoint.get('facts',{}).get('executable_revision')!=revision
        or checkpoint.get('source_unchanged') is not True or checkpoint.get('package_unchanged') is not True
        or checkpoint.get('scope')!='ACTUAL_SCOPED_NATIVE07_AT_OWNING_DEPTH_ONLY'
        or checkpoint.get('awake',{}).get('restored') is not True):raise ValueError('Complete historical preflight required')
if passed:relative=checkpoint['artifact_root_ref']
else:
    executions=list((PROJECT/('artifacts/q-'+revision[:7]+'-depth/worker-logs')).iterdir())
    if len(executions)!=1:raise ValueError('One exact failed preflight scope required')
    relative=(executions[0]/'PQR-07-native-artifacts').relative_to(PROJECT).as_posix()
if not re.fullmatch(r'artifacts/q-'+re.escape(revision[:7])+r'-depth/worker-logs/pqr-[0-9a-f]{32}/PQR-07-native-artifacts',relative):
    raise ValueError('Exact known historical output scope required')
output=PROJECT/relative;result=json.loads(capture(output/'pqr-result.json'))
if passed and result!=checkpoint['native_result']:raise ValueError('Historical native inventory differs')
for row in result['artifacts']:
    safe_relative(row['ref'])
    capture(output/row['ref'],row['hash'])
primary=captured[output/'native-observations.json'];observed=json.loads(primary)
if (observed.get('passed') is not passed or observed.get('group')!='PQR-07'
        or observed.get('identity')!=checkpoint['facts'] or observed.get('target')!=current_target()
        or passed and sha(primary)!=checkpoint['native_observations_hash']):raise ValueError('Historical subject differs')
if result['assertions']!=[dict(assertion_id=name,status='PASS' if passed else 'NOT_RUN',evidence_ref='native-observations.json',evidence_hash=sha(primary))
        for name in NATIVE_ASSERTIONS['PQR-07']]:raise ValueError('Complete historical assertion inventory required')
execution=json.loads(capture(stage/'native07-owning-depth-execution.json'))
if execution.get('label')!='native07-owning-depth' or execution.get('exit_code')!=(0 if passed else 2) or execution.get('tree_reaped') is not True:
    raise ValueError('Owned historical command cleanup required')
capture(stage/'native07-owning-depth.log',execution['log_hash'])
capture(BASE/'verify_publication_owning_depth.py',checkpoint['helper_hash'])
for name in ('native07-depth-helper-review.json','native07-depth-helper-final-review.json','retain_native07_depth_history.py'):
    capture(BASE/name)
target=ROOT/('status/codex/productization/S12/current-windows-'+revision[:7]+'-native07-depth')
prepared=[];bindings=[]
for number,(path,raw) in enumerate(sorted(captured.items(),key=lambda item:item[0].relative_to(PROJECT).as_posix()),1):
    ref=f'artifacts/a{number:04d}'+path.suffix
    if path.suffix=='.png' and raw.startswith(b'\x89PNG\r\n\x1a\n'):safe=raw
    else:safe=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','').encode()
    prepared.append((ref,safe));bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),retained_ref=ref,retained_hash=sha(safe)))
target.mkdir();(target/'artifacts').mkdir()
for ref,safe in prepared:(target/ref).write_bytes(safe)
disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',branch='codex/r7-productization-master-20261002',
    executable_revision=revision,scope='HISTORICAL_SCOPED_NATIVE07_AT_FULL_OWNING_DEPTH',
    native07='PASS' if passed else 'FAIL',full_software_qualification_credit='NONE',publication_root_chars=checkpoint['publication_root_chars'],
    subject=checkpoint['facts'],owned_tree_reaped=True,source_and_package_unchanged_at_execution=True,
    os_power_settings='UNCHANGED',additional_public_requests=0,cumulative_public_requests=8,
    private_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',master='IN_PROGRESS',artifacts=bindings)
(target/'disposition.json').write_text(json.dumps(disposition,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(bindings),revision=revision,scope=disposition['scope'])))
