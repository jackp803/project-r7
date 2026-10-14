"""Exact-clean finite fixture source/native checkpoints, never full PQR."""
from datetime import datetime,timezone
from dataclasses import asdict
import hashlib,json,os,subprocess,sys,threading
from pathlib import Path

BASE=Path(__file__).resolve().parent
REPO=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(REPO),str(REPO/'src'),str(REPO/'tools'),str(BASE.parent)]
from application.qualification import revision_fact,parse_result,_sanitize
from application.paper.inventory import fixed_profile,current_target
from application.paper.producer import _guard
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.processes import ResourceLimits,spawn_owned
from application.platform.resources import inspect_hardware
from local_windows_qualification_awake import awake_request

MODULES=('test_fixture_paper_case_recipe','test_fixture_sealed_input_backup','test_product_data_backup',
    'test_fixture_temporal_recipe','test_paper_native_driver','test_normal_fixture_worker',
    'test_normal_fixture_paper','test_fixture_recipe_flow')

def inputs():
    names=subprocess.check_output(['git','ls-files','--','src','tests','tools','ui','packaging','contracts',
        'docs/product/v0_2','status/PM_PAPER_RELEASE_MAPPING_DECISION_20261013.md'],cwd=REPO).decode().splitlines()
    return {name:'sha256:'+hashlib.sha256((REPO/name).read_bytes()).hexdigest() for name in names}

def main(stage,revision):
    if stage not in ('focused','native-faults'):raise ValueError('Fixed fixture stage required')
    revision_fact(REPO,revision,True);before=inputs()
    output=BASE/('fixture-'+stage+'-'+revision[:7]);create_private_directory(output)
    evidence=dict(stage=stage,revision=revision,started_at=datetime.now(timezone.utc).isoformat(),passed=False,
        scope='FINITE_SEALED_FIXTURE_CASE_BACKUP_RECOVERY_ONLY',full_pqr='NOT_QUALIFIED',ordinary_paper='NOT_QUALIFIED',
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        input_files=len(before),input_hashes=before,commands=[],tool_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    done=threading.Event();samples=[]
    def observe():
        while not done.is_set():
            h=inspect_hardware(BASE);samples.append(dict(actual_at=datetime.now(timezone.utc).isoformat(),
                available_memory_bytes=h.available_memory_bytes,physical_memory_bytes=h.physical_memory_bytes));done.wait(2)
    thread=threading.Thread(target=observe,daemon=True);thread.start()
    with awake_request() as awake:
        try:
            profile=fixed_profile(current_target())
            if stage=='focused':
                env=os.environ.copy();env.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
                member=next(m for m in profile['groups'][0]['members'] if m['directory']=='tests/application' and m['pattern']=='test_*.py')
                for name in MODULES:
                    path=output/(name+'.log')
                    with path.open('xb') as stream:
                        owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','discover','-s','tests/application',
                            '-p',name+'.py','-v'],cwd=REPO,env=env,limits=ResourceLimits(300),stdout=stream,stderr=subprocess.STDOUT)
                        code=owned.wait()
                    raw=_sanitize(path.read_text(encoding='utf-8',errors='replace'),REPO)
                    path.write_text(raw,encoding='utf-8',newline='\n');parsed=asdict(parse_result(raw,returncode=code))
                    expected=sum(case.split('.')[0]==name for case in member['test_cases'])
                    row=dict(module=name,exit_code=code,tree_reaped=owned.termination_report.reaped,expected_tests=expected,**parsed)
                    evidence['commands'].append(row)
                    if code or not row['tree_reaped'] or not expected or parsed['tests_run']!=expected or any(parsed[k] for k in ('failures','errors','skipped','expected_failures','unexpected_successes')):
                        raise ValueError('Exact fixture source command failed')
                evidence['tests_run']=sum(row['tests_run'] for row in evidence['commands']);evidence['passed']=True
            else:
                from verify_paper_faults import verify_slice
                package=BASE/('build-'+revision[:7])/'dist/R7';facts=verify_distribution(package)
                _guard(REPO,revision,package,facts,profile)
                observations=verify_slice(package,output,facts)
                evidence.update(native_identity=facts,observations=observations,
                    scenarios_passed=sum(row['passed'] is True for row in observations),scenarios_total=len(observations))
                evidence['passed']=len(observations)==6 and all(row['passed'] is True for row in observations)
                _guard(REPO,revision,package,facts,profile)
        except Exception as error:
            evidence.update(error_type=type(error).__name__,reason='FIXTURE_CHECKPOINT_FAILED',passed=False)
        finally:
            done.set();thread.join(timeout=3);evidence['host_samples']=samples
            revision_fact(REPO,revision,True)
            if before!=inputs():raise ValueError('Frozen checkpoint inputs changed')
            evidence['inputs_unchanged']=True;evidence['finished_at']=datetime.now(timezone.utc).isoformat();evidence['awake']=awake
    write_private_new(output/'checkpoint.json',(json.dumps(evidence,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('input_hashes','host_samples','observations','awake')}),flush=True)
    return 0 if evidence['passed'] else 2

if __name__=='__main__':raise SystemExit(main(sys.argv[1],sys.argv[2]))
