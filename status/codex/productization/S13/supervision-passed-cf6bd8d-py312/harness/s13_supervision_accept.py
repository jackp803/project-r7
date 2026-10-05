from pathlib import Path
import hashlib, json, re, sys
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import _sanitize,revision_fact
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
short=revision[:7];clean=dict(revision=revision,worktree='CLEAN')
source=project/f'artifacts/r7-productization-S13-supervision-qualified-{short}'
build=project/f'artifacts/r7-native-windows-supervision-{short}'
native=project/f'artifacts/r7-native-windows-supervision-smoke-{short}'
selected=project/f'artifacts/r7-native-selected-research-{short}'
report=json.loads((source/'qualification.json').read_bytes())
smoke=json.loads((native/'native-smoke.json').read_bytes())
research=json.loads((selected/'native-selected-research.json').read_bytes())
built=json.loads((build/'build-result.json').read_bytes())
assert report['passed'] and report['source_before']==report['source_after']==clean
assert len(report['commands'])==16+len(report['inventory'])==33
for command in report['commands']:
    assert command['passed'] and command['tree_reaped'] and command['source_after']==clean
    assert not any(command[k] for k in ('failures','errors','skipped','expected_failures','unexpected_successes'))
    assert hashlib.sha256((source/command['log']).read_bytes()).hexdigest()==command['log_sha256']
assert smoke['passed'] and smoke['scenario_count']==8 and len(smoke['commands'])==9
assert all(c['passed'] and c['tree_reaped'] for c in smoke['commands'])
assert smoke['identity']==research['identity']==built['identity']
assert smoke['identity']['executable_revision']==revision
assert research['passed'] and research['actual_job']['state']=='COMPLETE'
assert research['actual_job']['outcome']['strategy_lifecycle']=='CANDIDATE'
assert research['tree_reaped'] and research['worker_result']['tree_reaped']
assert research['product_path']=='EMPTY' and research['pythonpath']=='UNSET'
assert revision_fact(root,revision,True)==clean
target=root/f'status/codex/productization/S13/supervision-passed-{short}-py312';assert not target.exists()
target.mkdir(parents=True);index=[]
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def retain(original,relative,sanitize=True):
    raw=original.read_bytes()
    stored=_sanitize(raw.decode('utf-8').replace('\r\n','\n'),root).encode() if sanitize else raw
    path=target/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(stored)
    index.append(dict(original_ref=original.relative_to(project).as_posix(),retained_file=relative,original_sha256=digest(raw),retained_sha256=digest(stored),transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION' if sanitize else 'NONE'))
for file in sorted(source.iterdir()):
    if file.is_file():retain(file,'source/'+file.name)
for file in sorted(native.iterdir()):
    if file.is_file() and file.suffix in ('.json','.log') and file.name!='設定 空格.json':retain(file,'native/'+file.name)
retain(build/'build-result.json','native/build-result.json')
retain(build/'dist/R7/distribution.json','native/distribution.json',False)
retain(build/'dist/R7/licenses/inventory.json','native/license-inventory.json',False)
retain(selected/'native-selected-research.json','selected-native-research/native-selected-research.json')
retain(selected/'selected-native-worker.log','selected-native-research/selected-native-worker.log')
for number,file in enumerate(sorted((selected/'合成 本機 資料/worker-logs').glob('*.log')),1):retain(file,'selected-native-research/worker-logs/worker-'+str(number)+'.log')
for name in ('s13_supervision_qualify.py','s13_native_research_probe.py','s13_supervision_accept.py'):retain(project/'artifacts'/name,'harness/'+name)
for file in sorted((project/'artifacts').glob('S13-*.log')):retain(file,'development/'+file.name)
previous=project/'artifacts/r7-productization-S13-supervision-qualified-23e3f99'
for file in sorted(previous.iterdir()):
    if file.is_file():retain(file,'historical/failed-source-23e3f99/'+file.name)
previous=project/'artifacts/r7-productization-S13-supervision-qualified-f2e9703'
for file in sorted(previous.iterdir()):
    if file.is_file():retain(file,'historical/failed-source-f2e9703/'+file.name)
for folder in ('S13-timeout-profile-f2e9703','S13-timeout-profile-development-fingerprint'):
    previous=project/'artifacts'/folder
    for file in sorted(previous.iterdir()):
        if file.is_file() and file.suffix in ('.json','.log','.txt'):retain(file,'historical/'+folder+'/'+file.name)
retain(project/'artifacts/s13_timeout_profile_original_f2e9703.py','harness/s13_timeout_profile_original_f2e9703.py')
retain(project/'artifacts/s13_timeout_profile.py','harness/s13_timeout_profile.py')
prior_build=project/'artifacts/r7-native-windows-supervision-f2e9703'
retain(prior_build/'build-result.json','historical/scoped-native-f2e9703/build-result.json')
retain(prior_build/'dist/R7/distribution.json','historical/scoped-native-f2e9703/distribution.json',False)
retain(prior_build/'dist/R7/licenses/inventory.json','historical/scoped-native-f2e9703/license-inventory.json',False)
for folder in ('r7-native-windows-supervision-smoke-f2e9703','r7-native-selected-research-f2e9703'):
    previous=project/'artifacts'/folder
    kind='smoke' if 'smoke' in folder else 'research'
    for file in sorted(previous.glob('*.json')):
        if file.name in ('native-smoke.json','native-selected-research.json'):retain(file,'historical/scoped-native-f2e9703/'+kind+'/'+file.name)
    for file in sorted(previous.glob('*.log')):retain(file,'historical/scoped-native-f2e9703/'+kind+'/'+file.name)
    for number,file in enumerate(sorted(previous.glob('合成 本機 資料/worker-logs/*.log')),1):retain(file,'historical/scoped-native-f2e9703/'+kind+'/worker-logs/worker-'+str(number)+'.log')
for folder in ('r7-native-windows-supervision-smoke-23e3f99','r7-native-selected-research-23e3f99','r7-native-selected-research-23e3f99-local-inputs'):
    previous=project/'artifacts'/folder
    label='smoke-23e3f99' if 'smoke' in folder else 'research-local-inputs-23e3f99' if 'local-inputs' in folder else 'research-23e3f99'
    for file in sorted(previous.glob('*.json')):
        if file.name in ('native-smoke.json','native-selected-research.json'):retain(file,'historical/'+label+'/'+file.name)
    for file in sorted(previous.glob('*.log')):retain(file,'historical/'+label+'/'+file.name)
    for number,file in enumerate(sorted(previous.glob('合成 本機 資料/worker-logs/*.log')),1):retain(file,'historical/'+label+'/worker-logs/worker-'+str(number)+'.log')
(target/'original-to-retained.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
phases={p:sum(c['tests_run'] for c in report['commands'] if c['phase']==p) for p in ('phase_1','phase_2')}
facts=dict(executable_revision=revision,phase_1=phases['phase_1'],phase_2=phases['phase_2'],total=report['tests_run'],commands=len(report['commands']))
assert facts['total']==facts['phase_1']+facts['phase_2']
base=target.relative_to(root).as_posix()
progress_path=root/'coordination/CODEX/PROGRESS.json';progress=json.loads(progress_path.read_bytes())
assert progress['active_step']=='S13' and progress['steps']['S12']==progress['steps']['S13']=='IN_PROGRESS'
progress.update(executable_revision=revision,qualified_executable_revision=revision,next_step='S13 Windows supervisor/research checkpoint qualified; continue service/SSH/backup/recovery/runtime composition and S12/S14-S16; native Ubuntu remains NOT_RUN')
progress['tests_executed'].append(dict(step='S13',phase='EXACT_CLEAN_SOURCE_SUPERVISION',status='PASS',**facts,failures=0,errors=0,skipped=0,evidence_ref=base+'/source/qualification.json'))
progress['tests_executed'].append(dict(step='S13',phase='NATIVE_WINDOWS_SUPERVISION_AND_SYNTHETIC_RESEARCH_ONLY',status='PASS',executable_revision=revision,build_hash=smoke['identity']['build_hash'],scenarios=9,commands=10,research_namespace='LOCAL_RESEARCH',input_class='SYNTHETIC',failures=0,errors=0,skips=0,evidence_ref=base+'/native/native-smoke.json',selected_research_ref=base+'/selected-native-research/native-selected-research.json',scope='Actual frozen control/supervision and synthetic owned E2/E3/E5/E6 research only; no systemd/SSH/backup/runtime/real cloud/forward/provider/Ubuntu qualification'))
progress['evidence_refs'] += [base+'/source/qualification.json',base+'/native/native-smoke.json',base+'/selected-native-research/native-selected-research.json']
progress_path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=root/'coordination/CODEX/HANDOFF.md';prior=handoff.read_text(encoding='utf-8')
note='S13 exact-clean Windows/CPython3.12.10 supervisor/research checkpoint '+revision+': '+json.dumps(facts)+'. Native8 first-run/supervision plus1 selected synthetic E2/E3/E5/E6 research case PASS;10 commands/owned trees reaped;empty product PATH/PYTHONPATH unset. Frozen public LOCAL_RESEARCH publishes CANDIDATE from newly generated synthetic inputs,without financial authority. Build '+smoke['identity']['build_hash']+';archive SHA '+built['archive_sha256']+'. Evidence and original failed23e3f99 source/native runs retained under '+base+'. Source Git CLEAN and native worktreeUNAVAILABLE remain distinct. S12/S13 remain IN_PROGRESS;service/SSH/backup/restore/runtime/host faults/native Ubuntu/S14-S16 remain required. Next independent work:consistent backup/restore generation and service semantics,then continuous runtime/cloud/feedback/whole-product acceptance. New source changes require new clean qualification. SELF_REVIEW;S16 review pending. Real provider0,credentialsNONE,capitalNONE,GitHub computeNOT_USED,main mergeNOT_PERFORMED.\n\n'
handoff.write_text(note+prior,encoding='utf-8',newline='\n')
files=[dict(file=f.relative_to(root).as_posix(),sha256=digest(f.read_bytes())) for f in sorted(target.rglob('*')) if f.is_file()]
manifest=root/f'status/codex/productization/S13/supervision-artifact-hashes-{short}.json'
manifest.write_text(json.dumps({item['file']:item['sha256'] for item in files},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(**facts,retained_files=len(files),build_hash=smoke['identity']['build_hash'])))
