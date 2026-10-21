"""Exact-clean current Windows build/owning qualification/daemon execution."""
from contextlib import nullcontext
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess,sys,threading
from pathlib import Path

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(BASE.parent)]
from application.qualification import revision_fact,_sanitize
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.resources import inspect_hardware
from application.paper.producer import _guard,qualify
from application.paper.inventory import current_target,fixed_profile
from local_windows_qualification_awake import awake_request


def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()


def command(argv,output,label,timeout=1200):
    raw=output/(label+'.raw');log=output/(label+'.log');owned=None;code=None;cleanup=None
    with raw.open('xb') as stream:
        try:
            owned=spawn_owned(list(map(str,argv)),cwd=ROOT,limits=ResourceLimits(timeout),stdout=stream,stderr=subprocess.STDOUT)
            code=owned.wait()
        finally:
            if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
    text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    write_private_new(log,text.replace('\r\n','\n').encode());raw.unlink()
    facts=dict(label=label,exit_code=code,tree_reaped=bool(cleanup and cleanup.reaped),log_ref=log.name,log_hash=sha(log.read_bytes()))
    write_private_new(output/(label+'-execution.json'),(json.dumps(facts,indent=2)+'\n').encode())
    if code!=0 or not facts['tree_reaped']:raise ValueError('Actual owned checkpoint command failed')
    return json.loads(text)


def run(stage,revision,attempt='first'):
    if not re.fullmatch('[0-9a-f]{40}',revision) or not re.fullmatch('first|retry[0-9]{2}',attempt):raise ValueError('Fixed exact fresh attempt required')
    revision_fact(ROOT,revision,True)
    output=BASE/(stage+'-'+revision[:7]+'-'+attempt)
    if output.exists():raise ValueError('Fresh checkpoint output required')
    if stage not in ('build','qualify','headless','native05','native06','native07'):raise ValueError('Fixed local stage required')
    create_private_directory(output)
    report=dict(stage=stage,revision=revision,attempt=attempt,passed=False,source_worktree='CLEAN',
        started_at=datetime.now(timezone.utc).isoformat(),additional_provider_requests=0,cumulative_public_requests=8,
        cumulative_public_responses=8,credentials='NONE',private_requests=0,provider_mutation=0,capital='NONE',github_compute='NOT_USED',
        helper_hash=sha(Path(__file__).read_bytes()),master='IN_PROGRESS')
    done=threading.Event();samples=[]
    def sample():
        while not done.is_set():
            try:
                hardware=inspect_hardware(BASE)
                samples.append(dict(observed_at=datetime.now(timezone.utc).isoformat(),available_memory_bytes=hardware.available_memory_bytes,
                    physical_memory_bytes=hardware.physical_memory_bytes))
            except Exception as error:samples.append(dict(error_type=type(error).__name__))
            done.wait(2)
    monitor=threading.Thread(target=sample,daemon=True);monitor.start()
    scope=awake_request() if os.name=='nt' else nullcontext(dict(requested=False,restored=True))
    with scope as awake:
        try:
            if stage=='build':
                build=BASE/('build-'+revision[:7])
                result=command([PROJECT/'toolchains/py312-native-build/Scripts/python.exe','-X','utf8',ROOT/'tools/build_product.py',
                    '--output',build,'--expected-revision',revision],output,'native-build')
                report['result']=result
            else:
                package=BASE/('build-'+revision[:7])/'dist/R7'
                facts=verify_distribution(package);profile=fixed_profile(current_target())
                _guard(ROOT,revision,package,facts,profile)
                if stage=='qualify':
                    config=output/'product.json'
                    command([package/'R7.exe','init-profile','--config',config,'--data-root',output/'data',
                        '--instance-id','owning-current-'+revision[:7]],output,'init-owning')
                    result=qualify(config,ROOT,package);report['result']=result
                    if result['status']!='NATIVE_PAPER_SOFTWARE_QUALIFIED':raise ValueError('Owning complete qualification not passed')
                    observed=command([package/'R7.exe','_paper-release-observe','--config',config,'--receipt-ref',
                        result['receipt_ref'],'--mode','software'],output,'actual-native-software-readback',120)
                    if (observed['mode']!='software' or observed['runtime'] is not None or observed['selection_generation'] is not None
                            or any(observed['facts'].get(key)!=value for key,value in facts.items())):
                        raise ValueError('Actual final software receipt native readback differs')
                    report['actual_native_software_readback']=observed
                elif stage=='headless':
                    from verify_headless_product import verify
                    code=verify(package,output/'execution',research_input_root=BASE/'public-c62b11a-research/data')
                    if code!=0:raise ValueError('Actual native daemon incomplete')
                else:
                    from verify_paper_product import verify
                    if verify(package,output/'execution','PQR-'+stage[-2:])!=0:raise ValueError('Actual scoped native group incomplete')
                _guard(ROOT,revision,package,facts,profile)
            report['passed']=True
        except BaseException as error:
            report.update(passed=False,error_type=type(error).__name__)
        finally:
            done.set();monitor.join(timeout=3);report['host_samples']=samples
            report['finished_at']=datetime.now(timezone.utc).isoformat()
            revision_fact(ROOT,revision,True)
            report['source_unchanged']=True;report['awake']=awake
    write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({key:value for key,value in report.items() if key not in ('host_samples','result','awake')}),flush=True)
    return 0 if report['passed'] else 2


if __name__=='__main__':raise SystemExit(run(*sys.argv[1:]))
