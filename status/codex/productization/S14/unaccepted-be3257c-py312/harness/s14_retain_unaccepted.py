from pathlib import Path
import hashlib,json,sys
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import _sanitize,revision_fact
revision='be3257c20989f170631b749441b5ddaed1e2b227';short=revision[:7]
assert revision_fact(root,revision,True)==dict(revision=revision,worktree='CLEAN')
load=lambda path:json.loads(path.read_bytes())
digest=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()
target=root/'status/codex/productization/S14/unaccepted-be3257c-py312';assert not target.exists()
target.mkdir(parents=True);index=[]
def retain(file,relative,binary=False):
    original=file.read_bytes();raw=original if binary else _sanitize(original.decode('utf-8',errors='replace').replace('\r\n','\n'),root).encode()
    destination=target/relative;assert len(str(destination))<250
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
    index.append(dict(original_ref=file.relative_to(project).as_posix(),retained_file=relative,original_sha256=digest(original),retained_sha256=digest(raw),
        transformation='NONE' if binary else 'UTF8_REPLACEMENT_DECODE/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
def top(folder,label):
    for file in sorted(folder.iterdir()):
        if file.is_file() and file.suffix in ('.json','.log') and not file.name.startswith('設定'):retain(file,label+'/'+file.name)
attempts=[]
for suffix,label in (('','source-attempt-1'),('-retry-1','source-attempt-2')):
    folder=project/f'artifacts/r7-productization-S14-qualified-{short}{suffix}'
    report=load(folder/'qualification.json')
    assert not report['passed'] and report['source_before']==report['source_after']==dict(revision=revision,worktree='CLEAN')
    assert report['commands'][-1]['suite']=='product' and len(report['commands'])==32
    assert all(c['tree_reaped'] for c in report['commands'])
    attempts.append(dict(tests_run=report['tests_run'],commands=32,product_tests=162,product_errors=report['commands'][-1]['errors'],
        product_failures=report['commands'][-1]['failures'],registry='NOT_RUN_AFTER_FAIL_FAST',acceptance='NOT_ACCEPTED'))
    top(folder,label)
assert [a['product_errors'] for a in attempts]==[5,1]
top(project/'artifacts/r7-native-S14-smoke-be3257c','native-smoke')
top(project/'artifacts/r7-native-S14-cloud-be3257c','native-cloud')
for folder,name,label in (('r7-native-windows-S14-be3257c','build-result.json','native-build'),('r7-native-S14-research-be3257c','native-selected-research.json','native-research')):
    retain(project/'artifacts'/folder/name,label+'/'+name)
visual=project/'artifacts/S14-feedback-visual-be3257c'
retain(visual/'feedback-visual-qa.json','feedback-visual/feedback-visual-qa.json')
for file in visual.glob('*.png'):retain(file,'feedback-visual/'+file.name,True)
top(project/'artifacts/r7-productization-S14-qualified-9b77981','historical-9b/source')
for folder,name in (('r7-native-S14-smoke-9b77981','native-smoke.json'),('r7-native-S14-research-9b77981','native-selected-research.json'),('r7-native-S14-cloud-9b77981','native-S14.json'),('r7-native-windows-S14-9b77981','build-result.json')):
    retain(project/'artifacts'/folder/name,'historical-9b/'+name)
for file in sorted((project/'artifacts').glob('S14*.log')):retain(file,'development/'+file.name)
for name in ('s14_qualify.py','s14_native_probe.py','s14_stage_privacy_red.py','s14_feedback_visual_qa.mjs','S14LocalFakeRclone.cs','s14_retain_unaccepted.py'):
    retain(project/'artifacts'/name,'harness/'+name)
samples=load(project/'artifacts/r7-productization-S14-qualified-be3257c-retry-1/hardware-observations.json')['samples']
minimum=min(samples,key=lambda row:row['available_memory_bytes'])
facts=dict(candidate_executable_revision=revision,result='NOT_ACCEPTED',source_attempts=attempts,
    current_scoped_native=dict(scenarios=21,commands=22,result='PASS',scope='OFFLINE_TRANSPORT_SIMULATION_ONLY'),
    generated_feedback_viewports=2,full_source='FAIL',memory_samples=len(samples),minimum_sample=minimum,
    samples_below_admission_minimum=sum(row['available_memory_bytes']<row['existing_admission_minimum_bytes'] for row in samples),
    immediate_error='RESEARCH_MEMORY_PRESSURE',underlying_transient_cause='UNPROVEN;2-second external samples do not resolve instantaneous admission values',
    threshold_changes='NONE',historical_candidate=dict(revision='9b7798157f0ba4675f5f973a6b4ca622200695a5',source_tests=1762,
        scoped_native_scenarios=20,scoped_native_commands=21,result='NOT_ACCEPTED',reason='Privacy-before-stage RED'),
    accepted_executable_revision='7f50cbf4fdb339ac50ea98f0880de05e8546fb8a',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
    real_cloud='NOT_RUN',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',review='SELF_REVIEW;S16_PENDING')
(target/'disposition.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
(target/'original-to-retained.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
base=target.relative_to(root).as_posix();path=root/'coordination/CODEX/PROGRESS.json';progress=load(path)
assert progress['qualified_executable_revision']==facts['accepted_executable_revision']
progress.update(candidate_executable_revision=revision,active_step='S13',next_step='Fix reproduced fixture setup cleanup; integrate private fresh-generation restore and full user-data backup,service/SSH; repeat exact-clean qualification with instantaneous admission diagnostics. S14 forward feedback/S12/S15-S16 remain.')
progress['tests_executed'].append(dict(step='S14',phase='SOURCE_AND_NATIVE_UNACCEPTED_CANDIDATES',status='FAIL',**facts,evidence_ref=base+'/disposition.json'))
progress['evidence_refs'].append(base+'/disposition.json')
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=root/'coordination/CODEX/HANDOFF.md'
note='S14 candidates NOT_ACCEPTED:9b source1762/native20 scenarios passed but privacy-before-stage RED;corrected '+revision+' native21 scoped scenarios/22 commands and2 generated feedback viewport checks PASS,full source attempts each1719 tests/32 commands FAILED product162 with5 then1 RESEARCH_MEMORY_PRESSURE errors;registry NOT_RUN after fail-fast.480 host memory samples all above existing threshold;instantaneous cause remains UNPROVEN.No threshold/test bypass. Evidence '+base+'. Accepted executable remains7f50cbf4fdb339ac50ea98f0880de05e8546fb8a. Ordinary fixture setup handle leak independently reproduced;private database restore development7 tests passed outside frozen Git source but NOT_YET_INTEGRATED/NOT_NATIVE_QUALIFIED. Continue S13 cleanup/restore/full data/services,S12 runtime,S14 forward feedback,S15-S16. Raw private captures/DB/auth/session/config references/archives stay local. Provider0,credentialsNONE,capitalNONE,GitHub computeNOT_USED,main mergeNOT_PERFORMED.\n\n'
handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
files={file.relative_to(root).as_posix():digest(file.read_bytes()) for file in sorted(target.rglob('*')) if file.is_file()}
(root/'status/codex/productization/S14/unaccepted-artifact-hashes-be3257c.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(files),result='NOT_ACCEPTED',accepted_executable=facts['accepted_executable_revision'])))
