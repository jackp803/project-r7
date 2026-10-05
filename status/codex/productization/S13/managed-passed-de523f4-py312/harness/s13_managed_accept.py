from pathlib import Path
import hashlib,json,re,sys
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import _sanitize,revision_fact
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
short=revision[:7];clean=dict(revision=revision,worktree='CLEAN')
source=project/f'artifacts/r7-productization-S13-managed-qualified-{short}'
ui=project/f'artifacts/r7-productization-S13-managed-ui-qualified-{short}-safe-logs'
build=project/f'artifacts/r7-native-windows-managed-{short}'
native=project/f'artifacts/r7-native-windows-managed-smoke-{short}'
research=project/f'artifacts/r7-native-managed-research-{short}'
load=lambda path:json.loads(path.read_bytes())
report=load(source/'qualification.json');interface=load(ui/'ui-qualification.json')
smoke=load(native/'native-smoke.json');selected=load(research/'native-selected-research.json');built=load(build/'build-result.json')
assert report['passed'] and report['source_before']==report['source_after']==clean
assert len(report['commands'])==16+len(report['inventory'])==33
for command in report['commands']:
    assert command['passed'] and command['tree_reaped'] and command['source_after']==clean
    assert not any(command[k] for k in ('failures','errors','skipped','expected_failures','unexpected_successes'))
    assert hashlib.sha256((source/command['log']).read_bytes()).hexdigest()==command['log_sha256']
assert interface['passed'] and len(interface['commands'])==6 and interface['source_before']==interface['source_after']==clean
assert all(command['passed'] and command['tree_reaped'] and command['source_after']==clean for command in interface['commands'])
assert interface['commands'][3]['tests_passed']==15
browser=interface['commands'][5]['browser_stats']
assert browser['expected']==11 and browser['unexpected']==browser['skipped']==browser['flaky']==0
assert smoke['passed'] and smoke['scenario_count']==8 and len(smoke['commands'])==9
assert all(command['passed'] and command['tree_reaped'] for command in smoke['commands'])
assert smoke['identity']==selected['identity']==built['identity'] and built['source']['revision']==revision
assert built['source']['worktree']=='CLEAN' and built['identity']['executable_revision']==revision
assert built['source']['implementation_hash']==built['identity']['implementation_hash']
assert selected['passed'] and selected['tree_reaped'] and selected['worker_result']['tree_reaped']
assert selected['actual_job']['state']=='COMPLETE' and selected['actual_job']['outcome']['strategy_lifecycle']=='CANDIDATE'
assert selected['product_path']=='EMPTY' and selected['pythonpath']=='UNSET'
assert revision_fact(root,revision,True)==clean
target=root/f'status/codex/productization/S13/managed-passed-{short}-py312';assert not target.exists()
target.mkdir(parents=True);index=[]
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def retain(original,relative,sanitize=True):
    raw=original.read_bytes();stored=_sanitize(raw.decode('utf-8').replace('\r\n','\n'),root).encode() if sanitize else raw
    path=target/relative;path.parent.mkdir(parents=True,exist_ok=True)
    assert len(str(path))<250,'Retained evidence path must fit conservative Windows limits'
    path.write_bytes(stored)
    index.append(dict(original_ref=original.relative_to(project).as_posix(),retained_file=relative,original_sha256=digest(raw),retained_sha256=digest(stored),transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION' if sanitize else 'NONE'))
for folder,label in ((source,'source'),(ui,'ui'),(native,'native')):
    for file in sorted(folder.iterdir()):
        if file.is_file() and file.suffix in ('.json','.log','.png'):
            retain(file,label+'/'+file.name,file.suffix!='.png')
retain(build/'build-result.json','native/build-result.json')
retain(build/'dist/R7/distribution.json','native/distribution.json',False)
retain(build/'dist/R7/licenses/inventory.json','native/license-inventory.json',False)
retain(research/'native-selected-research.json','selected-research/native-selected-research.json')
retain(research/'selected-native-worker.log','selected-research/parent.log')
for number,file in enumerate(sorted(research.glob('合成 本機 資料/worker-logs/*.log')),1):retain(file,'selected-research/worker-'+str(number)+'.log')
for name in ('s13_managed_qualify.py','s13_managed_ui_qualify.py','s13_native_research_probe.py','s13_managed_accept.py'):
    retain(project/'artifacts'/name,'harness/'+name)
names=set()
for pattern in ('S13-managed*.log','S13-health*.log','S13-supervised-health*.log','S13-health*-RED-results.json','S13-supervised-health*-RED-results.json'):
    for file in sorted((project/'artifacts').glob(pattern)):
        if file.name not in names:retain(file,'development/'+file.name);names.add(file.name)
(target/'original-to-retained.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
base=target.relative_to(root).as_posix()
phases={p:sum(command['tests_run'] for command in report['commands'] if command['phase']==p) for p in ('phase_1','phase_2')}
facts=dict(executable_revision=revision,phase_1=phases['phase_1'],phase_2=phases['phase_2'],total=report['tests_run'],commands=33)
assert facts['total']==facts['phase_1']+facts['phase_2']
path=root/'coordination/CODEX/PROGRESS.json';progress=load(path)
assert progress['active_step']=='S13' and progress['steps']['S12']==progress['steps']['S13']=='IN_PROGRESS'
progress.update(executable_revision=revision,qualified_executable_revision=revision,next_step='S13 consistent backup/restore generation and service/SSH deployment; continue remaining S12 runtime/S14-S16; native Ubuntu remains NOT_RUN')
progress['tests_executed'].append(dict(step='S13',phase='EXACT_CLEAN_MANAGED_STOP_SOURCE',status='PASS',**facts,failures=0,errors=0,skipped=0,evidence_ref=base+'/source/qualification.json'))
progress['tests_executed'].append(dict(step='S13',phase='EXACT_CLEAN_MANAGED_HEALTH_UI',status='PASS',executable_revision=revision,commands=6,unit_tests=15,browser_tests=11,failures=0,errors=0,skipped=0,flaky=0,evidence_ref=base+'/ui/ui-qualification.json'))
progress['tests_executed'].append(dict(step='S13',phase='NATIVE_WINDOWS_MANAGED_STOP_CODE_AND_SYNTHETIC_RESEARCH_ONLY',status='PASS',executable_revision=revision,build_hash=smoke['identity']['build_hash'],scenarios=9,commands=10,failures=0,errors=0,skips=0,evidence_ref=base+'/native/native-smoke.json',selected_research_ref=base+'/selected-research/native-selected-research.json',scope='Fresh native Windows control/worker/start/restart/config drift/tamper and synthetic research only; no external console signal/systemd/SSH/backup/runtime/real cloud/forward/Ubuntu qualification'))
progress['evidence_refs'] += [base+'/source/qualification.json',base+'/ui/ui-qualification.json',base+'/native/native-smoke.json',base+'/selected-research/native-selected-research.json']
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=root/'coordination/CODEX/HANDOFF.md';prior=handoff.read_text(encoding='utf-8')
note='S13 managed-stop/health checkpoint '+revision+': '+json.dumps(facts)+'. Exact-clean UI6 commands/unit15/browser11 PASS;fresh native Windows9 scoped scenarios/10 owned commands PASS;build '+smoke['identity']['build_hash']+';archive SHA '+built['archive_sha256']+'. Evidence '+base+'. Actual source signals/control stop/owned descendant reaping and exact interrupted-job disposition are covered;native external-console/systemd/host faults are not qualified. Six UI screenshots retained;changed health views self-reviewed. Signal-under-held-lock RED and health/browser RED/GREEN preserved. Earlier233 supervision artifacts remain committed at2c5f3cb,not recopied or relabelled. S12/S13 IN_PROGRESS;continue consistent backup/restore generation,service/SSH,continuous runtime and S14-S16. Missing Ubuntu/cloud/real forward/provider commissioning NOT_RUN. SELF_REVIEW;independent S16 review pending. Real provider0,credentialsNONE,capitalNONE,GitHub computeNOT_USED,main mergeNOT_PERFORMED.\n\n'
handoff.write_text(note+prior,encoding='utf-8',newline='\n')
files={file.relative_to(root).as_posix():digest(file.read_bytes()) for file in sorted(target.rglob('*')) if file.is_file()}
(root/f'status/codex/productization/S13/managed-artifact-hashes-{short}.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(**facts,retained_files=len(files),build_hash=smoke['identity']['build_hash'])))
