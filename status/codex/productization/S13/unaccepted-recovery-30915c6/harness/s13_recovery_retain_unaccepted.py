from pathlib import Path
import hashlib,json,sys
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import _sanitize,revision_fact
revision='30915c6ebc599ad6562a748d754bdf515fa67ba0';short=revision[:7]
assert revision_fact(root,revision,True)==dict(revision=revision,worktree='CLEAN')
load=lambda p:json.loads(p.read_bytes())
digest=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()
target=root/f'status/codex/productization/S13/unaccepted-recovery-{short}';assert not target.exists()
target.mkdir(parents=True);index=[]
def retain(file,relative,binary=False):
    original=file.read_bytes();raw=original if binary else _sanitize(original.decode('utf-8',errors='replace').replace('\r\n','\n'),root).encode()
    path=target/relative;assert len(str(path))<250
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    index.append(dict(original_ref=file.relative_to(project).as_posix(),retained_file=relative,
        original_sha256=digest(original),retained_sha256=digest(raw),transformation='NONE' if binary else 'UTF8_REPLACEMENT_DECODE/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
for folder,label in (
    (f'r7-productization-S13-recovery-qualified-{short}','full-source'),
    (f'r7-productization-S13-recovery-ui-qualified-{short}-safe-logs','browser'),
    (f'r7-native-S13-recovery-smoke-{short}','native-smoke'),
    (f'r7-native-S13-recovery-research-{short}','native-research'),
    (f'r7-native-S13-recovery-cloud-{short}','native-cloud'),
    (f'r7-native-S13-recovery-restore-{short}','native-restore')):
    directory=project/'artifacts'/folder
    for file in sorted(directory.iterdir()):
        if file.is_file() and (file.suffix=='.log' or file.name in ('qualification.json','qualification-context.json','hardware-observations.json',
            'ui-qualification.json','browser-results.json','native-smoke.json','native-selected-research.json','native-S14.json','native-recovery.json')):
            retain(file,label+'/'+file.name)
        elif file.is_file() and label=='browser' and file.suffix=='.png':retain(file,label+'/'+file.name,True)
build=load(project/f'artifacts/r7-native-windows-S13-recovery-{short}/build-result.json')
retain(project/f'artifacts/r7-native-windows-S13-recovery-{short}/build-result.json','native-build/build-result.json')
for file in sorted((project/'artifacts').glob('S13*.log')):retain(file,'development/'+file.name)
retain(project/'artifacts/S13-independent-recovery-review.json','review/independent-review.json')
for name in ('s13_recovery_qualify.py','s13_recovery_ui_qualify.py','s13_native_recovery_probe.py','s13_native_harness_loopback_regression.py',
    's13_native_cloud_diagnose.py','s13_recovery_retain_unaccepted.py'):
    retain(project/'artifacts'/name,'harness/'+name)
facts=dict(candidate_executable_revision=revision,result='FAIL',acceptance='NOT_ACCEPTED',
    reason='MANDATORY_RETAINED_NATIVE_OFFLINE_BRIDGE_PUBLICATION_FAILURE',
    full_source=dict(result='PASS',tests=1786,commands=33,phase_1=247,phase_2=1539,failures=0,errors=0,skipped=0),
    browser=dict(result='PASS',commands=6,unit_tests=15,browser_tests=11,screenshots=6),
    native_smoke=dict(result='PASS',scenarios=8,commands=9),selected_native_research=dict(result='PASS',scenarios=1,commands=1),
    native_private_recovery=dict(result='PASS',scenarios=12,commands=15),
    native_offline_cloud=dict(result='FAIL',scenarios_passed_before_failure=8,commands_completed=9,
        failed_command='publish',attempted=2,cloud_acknowledged=1,unavailable=1,real_cloud='NOT_RUN'),
    diagnostic=dict(scope='SOURCE_OWNER_WITH_CONTROLLED_LOCAL_FAKE_ONLY',prestage_validation='PASS',
        failure='PUBLICATION_STAGE_WRITE_FAILED',formal_receipt_path_characters=228,temporary_path_characters=261,
        win32_last_error_after_cleanup=3,underlying_error='Win32 temporary path exceeds legacy MAX_PATH; add actual regression before minimal correction'),
    identity=build['identity'],archive_sha256=build['archive_sha256'],
    qualified_executable_revision='7f50cbf4fdb339ac50ea98f0880de05e8546fb8a',
    provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
    real_cloud='NOT_RUN',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',real_forward_paper='NOT_RUN',live='NOT_AUTHORIZED',
    next='Add long-path stage/read/author regressions; minimally fix explicit Win32 extended paths preserving pinned ancestor/reparse/copy-only behavior; establish new exact-clean candidate and repeat full/native/browser checks. Continue remaining master work.')
(target/'disposition.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
(target/'original-to-retained.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
path=root/'coordination/CODEX/PROGRESS.json';progress=load(path)
assert progress['qualified_executable_revision']==facts['qualified_executable_revision']
ref=target.relative_to(root).as_posix()
progress.update(candidate_executable_revision=revision,active_step='S13',next_step=facts['next'])
progress['tests_executed'].append(dict(step='S13',phase='EXACT_CLEAN_PRIVATE_RECOVERY_NATIVE_BRIDGE_FAILED',status='FAIL',evidence_ref=ref+'/disposition.json',**facts))
progress['evidence_refs'].append(ref+'/disposition.json')
progress['pending_recovery_checkpoint']=dict(status='FAIL',candidate_executable_revision=revision,acceptance='NOT_ACCEPTED',evidence_ref=ref+'/disposition.json')
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=root/'coordination/CODEX/HANDOFF.md'
note=(f'Candidate {revision} NOT_ACCEPTED:full source33 commands/1786 tests,15 UI+11 browser/6 screenshots,Windows native smoke8/9,research1/1,private recovery12/15 PASS;'
    'retained native offline bridge FAILED publish (8 scenarios passed,9 commands completed,2 attempts/1 ACK/1 unavailable). '
    'Actual source diagnostic:public pre-stage validation PASS;receipt path228 chars but temporary path261;PUBLICATION_STAGE_WRITE_FAILED. '
    f'Accepted executable remains {facts["qualified_executable_revision"]}. Evidence {ref}/disposition.json. '
    f'{facts["next"]} Source/recovery review has no remaining Important/Critical within bounded scope,not whole-branch acceptance. '
    'Private data/auth/session/backups/config/raw captures/native archives remain local within project root;provider0,credentialsNONE,capitalNONE,GitHub computeNOT_USED,main mergeNOT_PERFORMED.\n\n')
handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
files={file.relative_to(root).as_posix():digest(file.read_bytes()) for file in sorted(target.rglob('*')) if file.is_file()}
(root/f'status/codex/productization/S13/unaccepted-recovery-artifact-hashes-{short}.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(files),result='NOT_ACCEPTED',qualified_executable=facts['qualified_executable_revision'])))
