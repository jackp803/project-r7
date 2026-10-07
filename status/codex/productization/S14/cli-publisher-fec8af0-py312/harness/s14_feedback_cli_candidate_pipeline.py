"""Serial local qualification of one exact clean increment, retaining every result."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys
base=Path(__file__).resolve().parent;project=base.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import revision_fact,_sanitize
from application.platform.processes import ResourceLimits,spawn_owned
from application.platform.distribution import verify_distribution
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
short=revision[:7];python=str(sys.executable);build_python=str(project/'toolchains/py312-native-build/Scripts/python.exe')
build=base/f'r7-native-windows-S14-feedback-cli-{short}';package=build/'dist/R7'
outputs={name:base/f'r7-native-S14-feedback-cli-{name}-{short}' for name in ('smoke','research','cloud','restore','service','ssh')}
commands=[
 ('frontend',[python,str(base/'s14_feedback_cli_ui_frontend.py'),revision],900),
 ('native-build',[build_python,str(repo/'tools/build_product.py'),'--output',str(build),'--expected-revision',revision],1000),
 ('native-service-denial',[python,str(base/'s13_native_service_denial.py'),str(package),str(outputs['service'])],300),
 ('native-installer-denial',[python,str(base/'s14_feedback_cli_bound_installer.py'),revision],360),
 ('native-ssh-access',[python,str(base/'s13_native_ssh_probe.py'),str(package),str(outputs['ssh'])],300),
 ('native-smoke',[python,str(repo/'tools/verify_native_product.py'),'--package',str(package),'--output',str(outputs['smoke'])],600),
 ('native-research',[python,str(base/'s13_native_research_probe.py'),str(package),str(outputs['research'])],300),
 ('native-cloud',[python,str(base/'s14_native_probe.py'),str(package),str(outputs['research']),str(base/'S14LocalFakeRclone.exe'),str(outputs['cloud'])],600),
 ('native-restore',[python,str(base/'s13_native_recovery_probe.py'),str(package),str(outputs['restore'])],600),
 ('native-paper-feedback',[python,str(base/'s14_feedback_cli_native_paper.py'),str(package),str(base/'S14LocalFakeRclone.exe'),str(base/f'r7-native-S14-feedback-cli-paper-{short}')],600),
 ('full-source',[python,str(base/'s14_feedback_cli_source_qualify.py'),revision],3600),
 ('serial-browser',[python,str(base/'s14_feedback_cli_serial_browser_qualify.py'),revision],2400),
]
names=('s14_feedback_cli_candidate_pipeline.py','s14_feedback_cli_ui_frontend.py','s14_feedback_cli_bound_installer.py',
 's14_feedback_cli_source_qualify.py','s14_feedback_cli_serial_browser_qualify.py','s13_native_service_denial.py',
 's13_native_installer_denial_v2.py','s13_installer_package_binding.py','s13_native_ssh_probe.py','s13_native_access_integrity.py',
 's13_native_research_probe.py','s14_native_probe.py','s13_native_recovery_probe.py','s14_feedback_cli_native_paper.py','S14LocalFakeRclone.exe','S14LocalFakeRclone.cs')
hashes=lambda:{name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names}
before=hashes();identity=None
report=dict(revision=revision,worktree='CLEAN',commands=[],passed=False,harness_binding='BEFORE_AND_AFTER_EVERY_STAGE',
 harness_hashes=before,qualification_scope='S14_HISTORICAL_PAPER_PUBLICATION_COMPOSITION_WITH_WINDOWS_NATIVE_AND_BROWSER_REGRESSION',
 real_provider_requests=0,real_cloud='NOT_RUN',real_forward='NOT_RUN',credentials='NONE',capital='NONE',github_compute='NOT_USED',
 ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',normal_continuous_runtime_composition='PENDING_S12')
report_path=base/f'S14-feedback-cli-{short}-serial-pipeline.json';assert not report_path.exists()
stamp=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def persist():report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
for label,argv,timeout in commands:
 revision_fact(repo,revision,True);assert hashes()==before
 if identity is not None:assert verify_distribution(package)==identity
 log=base/f'S14-feedback-cli-{short}-{label}-pipeline.log';assert not log.exists();started=stamp()
 with log.open('xb') as stream:
  owned=spawn_owned(argv,cwd=repo,limits=ResourceLimits(timeout),stdout=stream,stderr=-2);code=owned.wait()
 text=_sanitize(log.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
 result=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,tree_reaped=owned.termination_report.reaped,
  passed=code==0 and owned.termination_report.reaped,log=log.name,log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())
 report['commands'].append(result);persist();print(json.dumps(result),flush=True)
 revision_fact(repo,revision,True);assert hashes()==before
 if label=='native-build' and result['passed']:
  identity=verify_distribution(package);assert identity['executable_revision']==revision;report['native_build_identity']=identity
 if identity is not None:assert verify_distribution(package)==identity
 if not result['passed']:raise SystemExit(1)
report['passed']=True;persist();print(json.dumps(dict(passed=True,stages=len(commands))))
