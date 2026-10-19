"""Actual strict native research-isolation probe; no full PQR credit."""
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,json,os,re,sys,traceback,uuid
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(BASE.parent)]
from application.qualification import revision_fact
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.paper.producer import _guard
from application.paper.inventory import current_target,fixed_profile
from local_windows_qualification_awake import awake_request
from run_current_checkpoint import command

def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

def child(revision,output):
    from verify_paper_isolation import NativeResearchIsolationFlow
    package=BASE/('build-'+revision[:7])/'dist/R7'
    facts=verify_distribution(package)
    if facts.get('executable_revision')!=revision:raise ValueError('Exact executable revision differs')
    profile=fixed_profile(current_target())
    _guard(ROOT,revision,package,facts,profile)
    flow=NativeResearchIsolationFlow(package,output,expected_identity=facts)
    report=dict(revision=revision,passed=False,scope='STRICT_SCOPED_NATIVE_ISOLATION_ONLY',
        full_qualification_credit='NONE',facts=facts,helper_hash=sha(Path(__file__).read_bytes()))
    try:
        observation=flow.run()
        if (observation.get('passed') is not True or observation.get('research_fault_protection_isolation') is not True
                or observation.get('host_bounded_capacity_measured') is not True):
            raise ValueError('Actual native isolation observations incomplete')
        report.update(passed=True,actual_research_target_pids=observation['actual_research_target_pids'],
            sample_count=observation['sample_count'],
            actual_target_concurrent_protected_samples=observation['actual_target_concurrent_protected_samples'],
            progress=observation['progress'],research_result=observation['research_result'])
    except Exception as error:
        frames=traceback.extract_tb(error.__traceback__)
        frame=frames[-1]
        # Record only a fixed literal already present in the public driver.
        tree=ast.parse((ROOT/'tools/verify_paper_isolation.py').read_text(encoding='utf-8'))
        literals={node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str)}
        report.update(error_type=type(error).__name__,
            reason=str(error) if str(error) in literals else 'UNCLASSIFIED_BOUNDED_FAILURE',
            failure_site=dict(file=Path(frame.filename).name,function=frame.name,line=frame.lineno))
    finally:
        _guard(ROOT,revision,package,facts,profile)
        report.update(source_unchanged=True,package_unchanged=True,
            cleanup_confirmed=flow.research_child is None and flow.runtime_child is None and flow.control is None)
    write_private_new(output/'probe-result.json',(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(report),flush=True)

def run(revision,attempt='probe01'):
    if os.name!='nt' or not re.fullmatch('[0-9a-f]{40}',revision) or not re.fullmatch('probe[0-9]{2}',attempt):
        raise ValueError('Exact Windows revision and fresh explicit probe required')
    revision_fact(ROOT,revision,True)
    package=BASE/('build-'+revision[:7])/'dist/R7';facts=verify_distribution(package)
    if facts.get('executable_revision')!=revision:raise ValueError('Exact executable revision differs')
    profile=fixed_profile(current_target());_guard(ROOT,revision,package,facts,profile)
    stage=BASE/('isolation-'+revision[:7]+'-'+attempt);create_private_directory(stage)
    data=PROJECT/'artifacts'/('q-'+revision[:7]+'-i00'+attempt[-2:]);create_private_directory(data)
    worker=data/'worker-logs';create_private_directory(worker)
    execution=worker/('pqr-'+uuid.uuid4().hex);create_private_directory(execution)
    native=execution/'PQR-05-native-artifacts';create_private_directory(native)
    output=native/'research-isolation'
    expected=PROJECT/'artifacts'/('q-'+revision[:7]+'-first')/'worker-logs'/('pqr-'+'0'*32)/'PQR-05-native-artifacts/research-isolation'
    assert len(str(output))==len(str(expected))
    report=dict(revision=revision,passed=False,facts=facts,started_at=datetime.now(timezone.utc).isoformat(),
        helper_hash=sha(Path(__file__).read_bytes()),artifact_root_ref=output.relative_to(PROJECT).as_posix(),
        scope='ACTUAL_STRICT_NATIVE_ISOLATION_AT_OWNING_DEPTH_ONLY',full_qualification_credit='NONE',
        additional_public_requests=0,cumulative_public_requests=8,private_requests=0,
        credentials='NONE',provider_mutation=0,capital='NONE',github_compute='NOT_USED')
    with awake_request() as awake:
        try:
            observed=command([sys.executable,'-X','utf8',Path(__file__),'--child',revision,output],stage,'actual-isolation',1200)
            if (observed.get('revision')!=revision or observed.get('facts')!=facts
                    or observed.get('passed') is not True or observed.get('cleanup_confirmed') is not True
                    or observed.get('source_unchanged') is not True or observed.get('package_unchanged') is not True):
                report['observed']=observed
                raise ValueError('Actual strict native isolation probe failed')
            report.update(passed=True,observed=observed)
        except Exception as error:
            report['error_type']=type(error).__name__
        finally:
            _guard(ROOT,revision,package,facts,profile)
            if sha(Path(__file__).read_bytes())!=report['helper_hash']:raise ValueError('Probe helper changed')
            report.update(source_unchanged=True,package_unchanged=True,finished_at=datetime.now(timezone.utc).isoformat(),awake=awake)
    write_private_new(stage/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in report.items() if k not in ('observed','awake')}),flush=True)
    return 0 if report['passed'] else 2

if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--child':child(sys.argv[2],Path(sys.argv[3]))
    else:raise SystemExit(run(*sys.argv[1:]))
