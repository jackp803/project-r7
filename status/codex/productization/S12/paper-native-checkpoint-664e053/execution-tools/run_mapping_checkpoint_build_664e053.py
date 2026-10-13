"""Exact clean scoped local checkpoint; source/native outcomes remain separate."""
from contextlib import nullcontext
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import subprocess,sys,threading,time

REPO=Path(r'<SOURCE_ROOT>')
BASE=Path(__file__).resolve().parent
REVISION=sys.argv[2]
sys.path[:0]=[str(REPO),str(REPO/'src'),str(REPO/'tools'),str(BASE.parent)]
from application.qualification import revision_fact,run_qualification
from application.paper.inventory import fixed_profile,current_target
from application.platform.private_files import create_private_directory,write_private_new
from application.paper.producer import _guard
from application.platform.distribution import verify_distribution
from application.platform.resources import inspect_hardware
from local_windows_qualification_awake import awake_request

def inputs():
    raw=subprocess.check_output(['git','ls-files','--','src','tests','tools','ui','packaging',
        'contracts','docs/product/v0_2','status/PM_PAPER_RELEASE_MAPPING_DECISION_20261013.md'],cwd=REPO)
    result={}
    for relative in raw.decode('utf-8').splitlines():
        path=REPO/relative
        result[relative]='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
    return result

def main(stage):
    revision_fact(REPO,REVISION,True)
    before=inputs();label=stage+'-'+REVISION[:7]
    output=BASE/label
    if output.exists():raise ValueError('Fresh execution output required')
    if stage!='build':create_private_directory(output)
    evidence=dict(stage=stage,revision=REVISION,started_at=datetime.now(timezone.utc).isoformat(),passed=False,
        source_worktree='CLEAN',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        input_files=len(before),input_hashes=before,tool_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        full_pqr='NOT_QUALIFIED',ordinary_paper='NOT_QUALIFIED')
    done=threading.Event();samples=[];sample_errors=[]
    def observe_host():
        while not done.is_set():
            try:
                host=inspect_hardware(BASE)
                samples.append(dict(observed_at=datetime.now(timezone.utc).isoformat(),
                    available_memory_bytes=host.available_memory_bytes,physical_memory_bytes=host.physical_memory_bytes))
            except Exception as error:sample_errors.append(type(error).__name__)
            done.wait(2)
    monitor=threading.Thread(target=observe_host,name='mapping-checkpoint-host-observer',daemon=True)
    monitor.start()
    scope=awake_request() if os.name=='nt' else nullcontext(dict(requested=False,restored=True))
    with scope as awake:
        try:
            if stage=='source':
                report=run_qualification(REPO,output,include_focused=True,suites=['all'],
                    expected_revision=REVISION,require_clean=True,timeout_seconds=900)
                evidence['passed']=report['passed'];evidence['tests_run']=report['tests_run']
                evidence['commands']=len(report['commands'])
                evidence['phases']={phase:dict(tests=sum(c['tests_run'] for c in report['commands'] if c['phase']==phase),
                    failures=sum(c['failures'] for c in report['commands'] if c['phase']==phase),
                    errors=sum(c['errors'] for c in report['commands'] if c['phase']==phase),
                    skipped=sum(c['skipped'] for c in report['commands'] if c['phase']==phase)) for phase in ('phase_1','phase_2')}
                expected=sum(len(m['test_cases']) for m in fixed_profile(current_target())['groups'][0]['members'])
                if report['tests_run']!=expected:evidence['passed']=False
            elif stage=='build':
                from application.platform.processes import ResourceLimits,spawn_owned
                from application.qualification import _sanitize
                build_python=REPO.parents[1]/'toolchains/py312-native-build/Scripts/python.exe'
                log=BASE/(label+'-build.log')
                evidence['build_interpreter_hash']='sha256:'+hashlib.sha256(build_python.read_bytes()).hexdigest()
                with log.open('xb') as stream:
                    child=spawn_owned([str(build_python),'-X','utf8',str(REPO/'tools/build_product.py'),
                        '--output',str(output),'--expected-revision',REVISION],cwd=REPO,
                        limits=ResourceLimits(1200),stdout=stream,stderr=subprocess.STDOUT)
                    code=child.wait()
                sanitized=_sanitize(log.read_text(encoding='utf-8',errors='replace'),REPO).replace(str(REPO.parents[1]),'<PROJECT_ROOT>')
                log.write_text(sanitized,encoding='utf-8',newline='\n')
                evidence['build_exit_code']=code;evidence['build_tree_reaped']=child.termination_report.reaped
                evidence['build_log_hash']='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest()
                if code!=0 or not child.termination_report.reaped:raise ValueError('Native build failed')
                report=json.loads((output/'build-result.json').read_bytes())
                evidence['passed']=True;evidence['build_result']=report
            else:
                package=BASE/('build-'+REVISION[:7])/'dist/R7'
                facts=verify_distribution(package);profile=fixed_profile(current_target())
                _guard(REPO,REVISION,package,facts,profile)
                if stage=='native02':
                    from verify_native_product import verify
                    code=verify(package,output)
                elif stage=='native03':
                    from verify_paper_product import verify
                    code=verify(package,output,'PQR-03')
                else:raise ValueError('Fixed stage required')
                evidence['passed']=code==0;evidence['native_identity']=facts
                _guard(REPO,REVISION,package,facts,profile)
        except Exception as error:
            evidence['error_type']=type(error).__name__;evidence['passed']=False
        finally:
            done.set();monitor.join(timeout=3)
            evidence['host_samples']=samples
            evidence['host_sample_errors']=sample_errors
            evidence['host_capacity_claim']='NONE;ACTUAL_HOST_OBSERVATION_ONLY'
            revision_fact(REPO,REVISION,True)
            if before!=inputs():raise ValueError('Exact checkpoint inputs changed')
            evidence['inputs_unchanged']=True
            evidence['finished_at']=datetime.now(timezone.utc).isoformat()
            evidence['awake']=awake
    if not output.exists():create_private_directory(output)
    raw=(json.dumps(evidence,indent=2)+'\n').encode('utf-8')
    if stage=='build':
        # The build tree contains distributable binary/public metadata only.
        # Do not claim private ACLs for the builder's ordinary output root.
        with (output/'checkpoint.json').open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    else:write_private_new(output/'checkpoint.json',raw)
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('input_hashes','build_result','awake','host_samples')}),flush=True)
    return 0 if evidence['passed'] else 2

if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
