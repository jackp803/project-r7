"""Serial exact-clean native then full-source qualification, project-local only."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,sys
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import revision_fact,_sanitize
from application.platform.processes import ResourceLimits,spawn_owned
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
short=revision[:7];base=project/'artifacts'
ui=json.loads((base/f'r7-productization-S13-recovery-ui-qualified-{short}-safe-logs/ui-qualification.json').read_bytes())
assert ui['qualification_scope']=='FRONTEND_ONLY' and ui['browser_status']=='NOT_RUN_PENDING_SERIAL_BROWSER'
assert ui['source_before']==dict(revision=revision,worktree='CLEAN')
assert len(ui['commands'])>=5 and all(c['passed'] for c in ui['commands'][:5])
assert ui['commands'][4]['command']==['npm','--prefix','ui','run','build']
build=base/f'r7-native-windows-S13-recovery-{short}'
package=build/'dist/R7'
outputs={name:base/f'r7-native-S13-recovery-{name}-{short}' for name in ('smoke','research','cloud','restore')}
python=Path(sys.executable)
build_python=project/'toolchains/py312-native-build/Scripts/python.exe'
commands=[
 ('native-build',[str(build_python),str(repo/'tools/build_product.py'),'--output',str(build),'--expected-revision',revision],1000),
 ('native-service-denial',[str(python),str(base/'s13_native_service_denial.py'),str(package),str(base/f'r7-native-S13-service-denial-{short}')],300),
 ('native-smoke',[str(python),str(repo/'tools/verify_native_product.py'),'--package',str(package),'--output',str(outputs['smoke'])],600),
 ('native-research',[str(python),str(base/'s13_native_research_probe.py'),str(package),str(outputs['research'])],300),
 ('native-cloud',[str(python),str(base/'s14_native_probe.py'),str(package),str(outputs['research']),str(base/'S14LocalFakeRclone.exe'),str(outputs['cloud'])],600),
 ('native-restore',[str(python),str(base/'s13_native_recovery_probe.py'),str(package),str(outputs['restore'])],600),
 ('full-source',[str(python),str(base/'s13_service_qualify.py'),revision],3600)]
report=dict(revision=revision,worktree='CLEAN',commands=[],passed=False,real_provider_requests=0,
    real_cloud='NOT_RUN',credentials='NONE',capital='NONE',github_compute='NOT_USED',
    initial_browser_status='NOT_RUN_PENDING_SERIAL_BROWSER',qualification_scope='S13_SERVICE_SUBJECT_AND_RETAINED_WINDOWS_RECOVERY',ubuntu_service_acceptance='NOT_RUN')
report_path=base/f'S13-recovery-{short}-serial-pipeline.json'
assert not report_path.exists()
stamp=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def persist():report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
for label,argv,timeout in commands:
    revision_fact(repo,revision,True)
    log=base/f'S13-recovery-{short}-{label}-pipeline.log';assert not log.exists()
    started=stamp()
    with log.open('xb') as stream:
        owned=spawn_owned(argv,cwd=repo,limits=ResourceLimits(timeout),stdout=stream,stderr=-2)
        code=owned.wait()
    text=_sanitize(log.read_text(encoding='utf-8',errors='replace'),repo)
    log.write_text(text,encoding='utf-8',newline='\n')
    result=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,
        tree_reaped=owned.termination_report.reaped,passed=code==0 and owned.termination_report.reaped,log=log.name)
    report['commands'].append(result);persist()
    print(json.dumps(result),flush=True)
    revision_fact(repo,revision,True)
    if not result['passed']:raise SystemExit(1)
report['passed']=True;persist()
print(json.dumps(dict(passed=True,commands=len(commands))))
