"""Exact-clean affected-owner source runs, original 900s per-module limit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,sys,time,unittest
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-qualification-cd415a1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import revision_fact,_sanitize
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.resources import _memory,GIB
from application.platform.private_files import create_private_directory,write_private_new
from strategy.v02.capabilities import _revision
revision=sys.argv[1];group=sys.argv[2];modules=sys.argv[3:]
if not modules or not group.replace('-','').isalnum():raise ValueError('Explicit safe group and modules required')
revision_fact(ROOT,revision,True);implementation=_revision()
def cases(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from cases(test)
        else:yield test.id()
identities={module:list(cases(unittest.defaultTestLoader.loadTestsFromName(module))) for module in modules}
all_ids=[item for values in identities.values() for item in values]
if len(all_ids)!=len(set(all_ids)) or any('_FailedTest' in case for case in all_ids):raise ValueError('Duplicate/failed discovery')
paths=sorted(list((ROOT/'tests').rglob('*.py')))
def pin():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
pins=pin();output=BASE/('h16-finalization-'+group+'-'+revision[:7]);create_private_directory(output)
started=datetime.now(timezone.utc).isoformat();results=[];samples=[]
for index,module in enumerate(modules,1):
    revision_fact(ROOT,revision,True)
    if _revision()!=implementation or pin()!=pins:raise ValueError('Subject changed before module')
    deadline=time.monotonic()+180
    while True:
        _,available=_memory();samples.append(dict(module=module,at=datetime.now(timezone.utc).isoformat(),available_bytes=available))
        if available>=6*GIB or time.monotonic()>=deadline:break
        time.sleep(10)
    if available<6*GIB:
        results.append(dict(module=module,status='NOT_RUN_RESOURCE_PREFLIGHT_BELOW_6GIB',passed=False));break
    owned=None;cleanup=None;failure_type=None;code=None;begin=datetime.now(timezone.utc).isoformat()
    rawpath=output/(str(index).zfill(3)+'.raw')
    try:
        with rawpath.open('xb') as stream:
            owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',module],cwd=ROOT,
                limits=ResourceLimits(900),stdout=stream,stderr=subprocess.STDOUT)
            code=owned.wait()
    except Exception as error:failure_type=type(error).__name__;code=-1
    finally:
        if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
    raw=rawpath.read_text(encoding='utf-8')
    safe=_sanitize(raw,ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
    safe='\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n'
    logfile=output/(str(index).zfill(3)+'.log');write_private_new(logfile,safe.encode());rawpath.unlink()
    counts=re.findall(r'Ran (\d+) tests? in ',safe);count=int(counts[-1]) if counts else None
    unchanged=_revision()==implementation and pin()==pins
    result=dict(module=module,expected_case_ids=identities[module],tests_run=count,exit_code=code,failure_type=failure_type,
        source_and_tests_unchanged=unchanged,tree_reaped=bool(cleanup and cleanup.reaped),log_ref=logfile.name,
        log_hash='sha256:'+hashlib.sha256(logfile.read_bytes()).hexdigest(),started_at=begin,
        finished_at=datetime.now(timezone.utc).isoformat())
    result['wall_elapsed_seconds']=(datetime.fromisoformat(result['finished_at'])-datetime.fromisoformat(begin)).total_seconds()
    result['within_original_wall_limit']=result['wall_elapsed_seconds']<=900
    result['passed']=result['within_original_wall_limit'] and code==0 and count==len(identities[module]) and '\nOK\n' in safe and 'skipped=' not in safe and unchanged and result['tree_reaped']
    results.append(result)
    (output/'progress.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(module=module,tests_run=count,passed=result['passed'])),flush=True)
    if not result['passed']:break
revision_fact(ROOT,revision,True)
report=dict(executable_revision=revision,implementation_hash=implementation,scope='EXACT_CLEAN_AFFECTED_OWNER_SOURCE_COMPONENTS',qualified_checkout='project-r7-qualification-cd415a1',
    modules=modules,results=results,tests_run=sum(row.get('tests_run') or 0 for row in results),
    passed=len(results)==len(modules) and all(row['passed'] for row in results),source_and_tests_unchanged=_revision()==implementation and pin()==pins,
    per_module_timeout_seconds=900,resource_samples=samples,test_file_hashes=pins,
    helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),started_at=started,
    finished_at=datetime.now(timezone.utc).isoformat(),native_full='NOT_RUN_FOR_THIS_SOURCE',master='IN_PROGRESS',
    public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,
    credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED')
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in report.items() if k not in ('results','test_file_hashes','resource_samples')}),flush=True)
raise SystemExit(0 if report['passed'] else 1)
