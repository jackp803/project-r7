from pathlib import Path
import hashlib,json,re,subprocess,sys
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import _sanitize,revision_fact
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
short=revision[:7];clean=dict(revision=revision,worktree='CLEAN')
source=project/f'artifacts/r7-productization-S13-backup-qualified-{short}'
build=project/f'artifacts/r7-native-windows-backup-{short}'
native=project/f'artifacts/r7-native-windows-backup-smoke-{short}'
research=project/f'artifacts/r7-native-backup-research-{short}'
snapshots=project/f'artifacts/r7-native-private-backup-{short}'
load=lambda path:json.loads(path.read_bytes())
report=load(source/'qualification.json');smoke=load(native/'native-smoke.json')
selected=load(research/'native-selected-research.json');snapshot=load(snapshots/'native-database-backup.json')
built=load(build/'build-result.json')
assert report['passed'] and report['source_before']==report['source_after']==clean
assert len(report['commands'])==16+len(report['inventory'])==33
for command in report['commands']:
    assert command['passed'] and command['tree_reaped'] and command['source_after']==clean
    assert not any(command[k] for k in ('failures','errors','skipped','expected_failures','unexpected_successes'))
    assert hashlib.sha256((source/command['log']).read_bytes()).hexdigest()==command['log_sha256']
assert smoke['passed'] and smoke['scenario_count']==8 and len(smoke['commands'])==9
assert all(command['passed'] and command['tree_reaped'] for command in smoke['commands'])
assert smoke['identity']==selected['identity']==snapshot['identity']==built['identity']
assert built['source']['revision']==revision and built['source']['worktree']=='CLEAN'
assert built['source']['implementation_hash']==built['identity']['implementation_hash']
assert selected['passed'] and selected['tree_reaped'] and selected['worker_result']['tree_reaped']
assert selected['actual_job']['state']=='COMPLETE' and selected['actual_job']['outcome']['strategy_lifecycle']=='CANDIDATE'
assert snapshot['passed'] and snapshot['scenario_count']==5 and len(snapshot['commands'])==7
assert all(command['passed'] and command['tree_reaped'] for command in snapshot['commands'])
assert all(scenario['passed'] for scenario in snapshot['scenarios'])
assert snapshot['snapshot_summary']['database_count']==4 and snapshot['restore']=='NOT_PERFORMED'
assert all(result['product_path']=='EMPTY' and result['pythonpath']=='UNSET' for result in (smoke,selected,snapshot))
ui_revision='de523f46a8ff196d90d1d13cfc55d76d5bd6cdd5'
historical_ui=root/'status/codex/productization/S13/managed-passed-de523f4-py312/ui/ui-qualification.json'
interface=load(historical_ui)
assert interface['passed'] and interface['source_before']==interface['source_after']==dict(revision=ui_revision,worktree='CLEAN')
assert interface['commands'][3]['tests_passed']==15
assert all(interface['commands'][5]['browser_stats'][key]==value for key,value in dict(expected=11,unexpected=0,flaky=0,skipped=0).items())
subprocess.run(['git','diff','--exit-code',ui_revision,revision,'--','ui','src/application/control_api','contracts/control_api_v0_2.openapi.json'],cwd=root,check=True,capture_output=True,timeout=10)
for relative,digest in interface['build_hashes'].items():
    assert 'sha256:'+hashlib.sha256((root/'ui/dist'/relative).read_bytes()).hexdigest()==digest
    assert 'sha256:'+hashlib.sha256((build/'dist/R7/_internal/ui'/relative).read_bytes()).hexdigest()==digest
assert revision_fact(root,revision,True)==clean
target=root/f'status/codex/productization/S13/backup-passed-{short}-py312';assert not target.exists()
target.mkdir(parents=True);index=[]
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def retain(original,relative,sanitize=True):
    raw=original.read_bytes();stored=_sanitize(raw.decode('utf-8').replace('\r\n','\n'),root).encode() if sanitize else raw
    path=target/relative;path.parent.mkdir(parents=True,exist_ok=True);assert len(str(path))<250
    path.write_bytes(stored)
    index.append(dict(original_ref=original.relative_to(project).as_posix(),retained_file=relative,
        original_sha256=digest(raw),retained_sha256=digest(stored),transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION' if sanitize else 'NONE'))
for folder,label in ((source,'source'),(native,'native'),(snapshots,'snapshot-native')):
    for file in sorted(folder.iterdir()):
        if file.is_file() and file.suffix in ('.json','.log') and not file.name.startswith('設定'):
            retain(file,label+'/'+file.name)
retain(build/'build-result.json','native/build-result.json')
retain(build/'dist/R7/distribution.json','native/distribution.json',False)
retain(build/'dist/R7/licenses/inventory.json','native/license-inventory.json',False)
retain(research/'native-selected-research.json','selected-research/native-selected-research.json')
retain(research/'selected-native-worker.log','selected-research/parent.log')
for number,file in enumerate(sorted(research.glob('合成 本機 資料/worker-logs/*.log')),1):retain(file,'selected-research/worker-'+str(number)+'.log')
for name in ('s13_backup_qualify.py','s13_native_backup_probe.py','s13_native_research_probe.py','s13_backup_accept.py'):
    retain(project/'artifacts'/name,'harness/'+name)
for file in sorted((project/'artifacts').glob('S13-backup*.log')):retain(file,'development/'+file.name)
ui_fact=dict(status='HISTORICAL_UNCHANGED_UI_VERIFIED',executable_revision=ui_revision,
    evidence_ref=historical_ui.relative_to(root).as_posix(),unit_tests=15,browser_tests=11,
    source_inputs_unchanged=True,current_and_native_asset_hashes=interface['build_hashes'],rerun_for_current_candidate=False)
(target/'unchanged-ui.json').write_text(json.dumps(ui_fact,indent=2)+'\n',encoding='utf-8',newline='\n')
(target/'original-to-retained.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
base=target.relative_to(root).as_posix()
phases={p:sum(command['tests_run'] for command in report['commands'] if command['phase']==p) for p in ('phase_1','phase_2')}
facts=dict(executable_revision=revision,phase_1=phases['phase_1'],phase_2=phases['phase_2'],total=report['tests_run'],commands=33)
assert facts['total']==facts['phase_1']+facts['phase_2']
path=root/'coordination/CODEX/PROGRESS.json';progress=load(path)
assert progress['active_step']=='S13' and progress['steps']['S12']==progress['steps']['S13']=='IN_PROGRESS'
progress.update(executable_revision=revision,qualified_executable_revision=revision,
    next_step='S13 full user-data restore generation/fencing and service/SSH; S12 continuous runtime; S14-S16 remain; Ubuntu NOT_RUN')
progress['tests_executed'].append(dict(step='S13',phase='EXACT_CLEAN_PRIVATE_DATABASE_BACKUP_SOURCE',status='PASS',**facts,
    failures=0,errors=0,skipped=0,evidence_ref=base+'/source/qualification.json'))
progress['tests_executed'].append(dict(step='S13',phase='NATIVE_WINDOWS_PRIVATE_DATABASE_SNAPSHOT_AND_EXISTING_SMOKE_ONLY',status='PASS',
    executable_revision=revision,build_hash=smoke['identity']['build_hash'],scenarios=14,commands=17,
    failures=0,errors=0,skips=0,evidence_ref=base+'/snapshot-native/native-database-backup.json',
    existing_smoke_ref=base+'/native/native-smoke.json',selected_research_ref=base+'/selected-research/native-selected-research.json',
    scope='Five actual native private database snapshot scenarios/seven commands, eight prior smoke scenarios/nine commands, one fresh synthetic selected research scenario/one command. No restore/runtime/installed-services/SSH/host-fault/Ubuntu commissioning qualification.'))
progress['evidence_refs'] += [base+'/source/qualification.json',base+'/snapshot-native/native-database-backup.json',base+'/native/native-smoke.json',base+'/selected-research/native-selected-research.json',base+'/unchanged-ui.json']
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=root/'coordination/CODEX/HANDOFF.md';prior=handoff.read_text(encoding='utf-8')
note='S13 private database snapshot checkpoint '+revision+': '+json.dumps(facts)+'. Native14 scoped scenarios/17 owned commands PASS;build '+smoke['identity']['build_hash']+';archive SHA '+built['archive_sha256']+'. Evidence '+base+'. Private snapshot DB/auth/session artifacts stay local;only sanitized proof retained. Backup grants no financial authority and performs no restore. Prior exact-clean de523f4 UI unit15/browser11 remains historical;tracked UI/API inputs and actual current/native asset bytes verified unchanged,not relabelled as a new UI run. S12/S13 IN_PROGRESS;continue full user-data restore generation/fencing,service/SSH,continuous runtime and S14-S16. Ubuntu/cloud/real forward/provider commissioning NOT_RUN. SELF_REVIEW;S16 independent review pending. Provider0,credentialsNONE,capitalNONE,GitHub computeNOT_USED,main mergeNOT_PERFORMED.\n\n'
handoff.write_text(note+prior,encoding='utf-8',newline='\n')
files={file.relative_to(root).as_posix():digest(file.read_bytes()) for file in sorted(target.rglob('*')) if file.is_file()}
(root/f'status/codex/productization/S13/backup-artifact-hashes-{short}.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(**facts,retained_files=len(files),build_hash=smoke['identity']['build_hash'])))
