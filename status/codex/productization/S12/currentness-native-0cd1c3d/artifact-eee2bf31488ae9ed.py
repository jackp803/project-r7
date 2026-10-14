"""Exact clean scoped currentness checks, no complete PQR/ordinary eligibility."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict
import hashlib,json,os,socket,subprocess,sys,threading,time
BASE=Path(__file__).resolve().parent;REPO=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
stage,revision=sys.argv[1:3]
attempt=sys.argv[3] if len(sys.argv)==4 else None
if attempt not in (None,'retry01'):raise ValueError('Fixed fresh retry required')
sys.path[:0]=[str(REPO),str(REPO/'src'),str(REPO/'tools'),str(BASE.parent)]
from application.qualification import revision_fact,parse_result,_sanitize
from application.paper.inventory import fixed_profile,current_target
from application.paper.producer import _guard
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.processes import ResourceLimits,spawn_owned
from application.platform.resources import inspect_hardware
from local_windows_qualification_awake import awake_request

def inputs():
    refs=subprocess.check_output(['git','ls-files','--','src','tests','tools','ui','packaging','contracts','docs/product/v0_2','status/PM_PAPER_RELEASE_MAPPING_DECISION_20261013.md'],cwd=REPO).decode().splitlines()
    return {ref:'sha256:'+hashlib.sha256((REPO/ref).read_bytes()).hexdigest() for ref in refs}

def main():
    if stage not in ('focused','native-negative'):raise ValueError('Fixed scoped stage required')
    revision_fact(REPO,revision,True);before=inputs()
    out=BASE/('currentness-'+stage+'-'+revision[:7]+('-'+attempt if attempt else ''));create_private_directory(out)
    report=dict(stage=stage,revision=revision,passed=False,started_at=datetime.now(timezone.utc).isoformat(),
        scope='EXACT_CLEAN_FOCUSED_SOURCE_ONLY' if stage=='focused' else 'ACTUAL_NATIVE_VERIFIER_AND_PUBLIC_NEGATIVE_ONLY',
        input_hashes=before,input_files=len(before),commands=[],full_pqr='NOT_QUALIFIED',ordinary_paper='NOT_QUALIFIED',
        native_positive_observation='NOT_RUN',native_protected_isolation='NOT_RUN',
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        tool_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    samples=[];done=threading.Event()
    def sample():
        while not done.is_set():
            host=inspect_hardware(BASE);samples.append(dict(at=datetime.now(timezone.utc).isoformat(),
                available_memory_bytes=host.available_memory_bytes,physical_memory_bytes=host.physical_memory_bytes))
            done.wait(2)
    monitor=threading.Thread(target=sample,daemon=True);monitor.start()
    def command(name,argv,*,expected=0,deadline=120,env=None):
        raw_path=out/(name+'.raw');started=time.monotonic()
        with raw_path.open('xb') as stream:
            child=spawn_owned(argv,cwd=REPO,limits=ResourceLimits(deadline),stdout=stream,stderr=subprocess.STDOUT,env=env)
            code=child.wait()
        raw=raw_path.read_bytes()
        if len(raw)>4*1024*1024:raise ValueError('Bounded observed output required')
        log=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(REPO.parents[1]),'<PROJECT_ROOT>').replace('<USER_HOME>','<USER_HOME>')
        write_private_new(out/(name+'.log'),log.encode());raw_path.unlink()
        item=dict(command=name,exit_code=code,expected_exit_code=expected,tree_reaped=child.termination_report.reaped,
            observed_elapsed_seconds=time.monotonic()-started,log=name+'.log',log_hash='sha256:'+hashlib.sha256(log.encode()).hexdigest())
        report['commands'].append(item)
        if code!=expected or not child.termination_report.reaped:raise ValueError('Actual scoped command failed or unreaped')
        return raw.decode('utf-8',errors='replace'),item
    with awake_request() as awake:
        try:
            if stage=='focused':
                env=os.environ.copy();env.update(PYTHONPATH=str(REPO/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
                for label,pattern in (('adapter-observation','test_native_paper_release_*.py'),('ordinary','test_ordinary_paper_*.py')):
                    raw,item=command(label,[sys.executable,'-X','utf8','-m','unittest','discover','-s','tests/application','-p',pattern,'-v'],env=env)
                    result=asdict(parse_result(raw.replace('\r\n','\n'),returncode=0));item['test_result']=result
                    if not result['passed'] or result['tests_run']==0:raise ValueError('Actual focused cases must pass')
                report['tests_run']=sum(c['test_result']['tests_run'] for c in report['commands'])
                if report['tests_run']!=28:raise ValueError('Exact focused count required')
            else:
                package=BASE/('build-'+revision[:7])/'dist/R7'
                facts=verify_distribution(package);_guard(REPO,revision,package,facts,fixed_profile(current_target()))
                report['identity']=facts;exe=package/json.loads((package/'distribution.json').read_bytes())['entrypoint']
                env={k:os.environ[k] for k in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if k in os.environ};env.update(PATH='',PYTHONUTF8='1')
                config=out/'product.json';data=out/'data';profile=out/'explicit-negative-selection.json'
                with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
                command('init',[str(exe),'init-profile','--config',str(config),'--data-root',str(data),
                    '--instance-id','native-currentness-negative-'+revision[:7],'--enable-paper-runtime','--port',str(port)],env=env)
                ref='qualification-'+'a'*64
                write_private_new(profile,(json.dumps(dict(schema_version='r7-local-paper-inputs-v0.2',
                    submission_id='synthetic-no-accepted-strategy',simulation_policy_ref='inputs/not-created-simulation.json',
                    risk_policy_ref='inputs/not-created-risk.json',promotion_policy_ref='inputs/not-created-promotion.json',
                    paper_policy_ref='synthetic-negative-policy',actor='synthetic-native-negative',workflow_authorized=False,
                    account_ref='NO_FUNDS_SYNTHETIC_REFERENCE',qualification_receipt_ref=ref))+'\n').encode())
                for index in range(3):
                    command('actual-private-verifier-'+str(index),[str(exe),'_paper-release-observe','--config',str(config),
                        '--receipt-ref',ref,'--mode','software'],expected=2,deadline=35,env=env)
                for index in range(3):
                    raw,item=command('public-configure-negative-'+str(index),[str(exe),'configure-paper','--config',str(config),
                        '--selection-profile',str(profile)],expected=2,deadline=35,env=env)
                    diagnostics=[json.loads(line) for line in raw.splitlines() if line.startswith('{')]
                    if len(diagnostics)!=1 or diagnostics[0].get('schema_version')!='r7-startup-diagnostic-v0.2':
                        raise ValueError('Actual sanitized public denial diagnostic required')
                    item['diagnostic']=diagnostics[0]
                    if item['observed_elapsed_seconds']>25:raise ValueError('Bounded public negative verifier exceeded observation cap')
                if any((data/leaf).exists() for leaf in ('canonical.sqlite3','process-supervision.sqlite','queue.sqlite')):
                    raise ValueError('Rejected native selection created canonical/runtime/research state')
                report.update(denied_selection_created_no_canonical_runtime_or_queue=True,
                    measurement='First/following native denial calls only; not complete qualified-receipt positive timing')
                _guard(REPO,revision,package,facts,fixed_profile(current_target()))
            report['passed']=True
        except Exception as error:report.update(passed=False,error_type=type(error).__name__)
        finally:
            done.set();monitor.join(timeout=3);revision_fact(REPO,revision,True)
            if before!=inputs():raise ValueError('Exact clean checkpoint input mutation')
            report.update(inputs_unchanged=True,host_samples=samples,finished_at=datetime.now(timezone.utc).isoformat(),awake=awake)
    write_private_new(out/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in report.items() if k not in ('input_hashes','host_samples','awake')},ensure_ascii=False))
    return 0 if report['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
