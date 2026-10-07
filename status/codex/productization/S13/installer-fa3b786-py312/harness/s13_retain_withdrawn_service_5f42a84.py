"""Retain bounded actual withdrawn attempt, never private profiles or raw data."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import _sanitize
revision='5f42a84e8e3b246bc569d093b8a8b1b4e4c8ac90';short=revision[:7]
base=project/'artifacts'
target=repo/f'status/codex/productization/S13/withdrawn-service-{short}'
assert not target.exists();target.mkdir(parents=True)
digest=lambda data:'sha256:'+hashlib.sha256(data).hexdigest()
load=lambda path:json.loads(path.read_bytes())
index=[]
def retain(file,label):
    raw=file.read_bytes()
    retained=_sanitize(raw.decode('utf-8',errors='replace').replace('\r\n','\n'),repo).encode('utf-8')
    path=target/label;assert len(str(path))<250
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(retained)
    index.append(dict(original_ref=file.relative_to(project).as_posix(),retained_file=label,
        original_sha256=digest(raw),retained_sha256=digest(retained),transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
def top(folder,label,names):
    for file in sorted(folder.iterdir()):
        if file.is_file() and (file.suffix=='.log' or file.name in names):retain(file,label+'/'+file.name)
source=base/f'r7-productization-S13-recovery-qualified-{short}'
full=load(source/'qualification.json')
assert not full['passed']
completed=full['commands']
assert all(c['passed'] and c['tree_reaped'] for c in completed)
top(source,'partial-source',{'qualification.json'})
uiroot=base/f'r7-productization-S13-recovery-ui-qualified-{short}-safe-logs'
ui=load(uiroot/'ui-qualification.json')
assert ui['passed'] and ui['qualification_scope']=='FRONTEND_ONLY' and len(ui['commands'])==5
top(uiroot,'frontend-only',{'ui-qualification.json'})
native=[]
for name in ('smoke','research','cloud','restore'):
    folder=base/f'r7-native-S13-recovery-{name}-{short}'
    report_name={'smoke':'native-smoke.json','research':'native-selected-research.json','cloud':'native-S14.json','restore':'native-recovery.json'}[name]
    data=load(folder/report_name);assert data['passed'] and data['identity']['executable_revision']==revision
    native.append(dict(name=name,passed=True))
    top(folder,'native-'+name,{report_name})
denial=base/f'r7-native-S13-service-denial-{short}'
data=load(denial/'native-service-denial.json');assert data['passed']
top(denial,'native-denial',{'native-service-denial.json'})
retain(base/f'r7-native-windows-S13-recovery-{short}/build-result.json','native-build/build-result.json')
pipeline=load(base/f'S13-recovery-{short}-serial-pipeline.json')
assert not pipeline['passed'] and len(pipeline['commands'])==6 and all(c['passed'] and c['tree_reaped'] for c in pipeline['commands'])
retain(base/f'S13-recovery-{short}-serial-pipeline.json','pipeline/partial-pipeline.json')
for file in sorted(base.glob(f'S13-recovery-{short}-*-pipeline.log')):retain(file,'pipeline/'+file.name)
facts=dict(schema_version='r7-withdrawn-service-candidate-v0.2',candidate=revision,result='WITHDRAWN_NOT_ACCEPTED',
    recorded_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
    cause='Independent Important renderer finding: plain tmpfiles mode/user/group can normalize existing scope inode before startup guard rejects mismatch',
    disposition='Pipeline interrupted by Codex after native scopes completed, before complete full-source/browser qualification; retain all observed outcomes',
    source=dict(result='INCOMPLETE_INTERRUPTED_NOT_ACCEPTED',completed_commands=len(completed),
        completed_tests=sum(c['tests_run'] for c in completed),
        completed_failures=sum(c['failures'] for c in completed),completed_errors=sum(c['errors'] for c in completed),
        completed_skips=sum(c['skipped'] for c in completed),unfinished_command='NOT_COUNTED;RAW_CAPTURE_REMAINS_LOCAL',
        final_owned_reaping='NOT_RECORDED_FOR_INTERRUPTED_COMMAND;NO_FALSE_PASS'),
    frontend='5_COMMANDS_PASS_ONLY;BROWSER_NOT_RUN',native=native,windows_native_denial='3_SCENARIOS_PASS',
    accepted_executable_unchanged='86643c4b0444db2cfb33ce071618c1e3f708ad37',
    ubuntu='NOT_RUN',systemd='NOT_RUN',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
    private_artifacts='PROFILES/DATABASES/RAW_CAPTURES/NATIVE_ARCHIVES_REMAIN_LOCAL',next='Creation-only tmpfiles regression and minimal fix; new exact-clean candidate')
(target/'disposition.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
(target/'original-to-retained.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
files={f.relative_to(repo).as_posix():digest(f.read_bytes()) for f in sorted(target.rglob('*')) if f.is_file()}
manifest=repo/f'status/codex/productization/S13/withdrawn-service-hashes-{short}.json'
manifest.write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8',newline='\n')
p=repo/'coordination/CODEX/PROGRESS.json';progress=load(p)
progress['service_increment'].update(status='REMEDIATED_QUALIFICATION_PENDING',service_tests_passed=36,
    withdrawn_candidate=revision,withdrawn_evidence=target.relative_to(repo).as_posix()+'/disposition.json',
    creation_only_scope_regression='RED14_TESTS_1_FAILURE;GREEN36_SERVICE_TESTS',boot_scope_enforcement='NATIVE_UBUNTU_NOT_RUN')
p.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
h=repo/'coordination/CODEX/HANDOFF.md'
note=f'S13 service candidate {revision} WITHDRAWN_NOT_ACCEPTED for Important plain-tmpfiles scope owner/mode normalization. Native scoped probes/frontend completed;full-source interrupted after{len(completed)} complete commands/{sum(c["tests_run"] for c in completed)} observed tests;browserNOT_RUN;unfinished command not counted. Evidence {target.relative_to(repo).as_posix()}/disposition.json. Creation-only mode/user/group regression RED14tests1fail,all36service testsGREEN. Establish new exact-clean candidate and rerun. Accepted86643c4 unchanged;Ubuntu/systemdNOT_RUN. Continue master on same branch.\n\n'
h.write_text(note+h.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(files),completed_source_commands=len(completed),completed_source_tests=sum(c['tests_run'] for c in completed),result='WITHDRAWN_NOT_ACCEPTED')))
