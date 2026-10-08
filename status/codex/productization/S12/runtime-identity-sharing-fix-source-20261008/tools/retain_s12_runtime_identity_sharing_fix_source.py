"""Retain fixed public failed-source and fixture-remediation evidence only."""
from pathlib import Path
import json,sys
BASE=Path(__file__).resolve().parent;REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(REPO/'src'))
from s09_owner_worker_native_regression import sha,stamp
from application.datasets.catalog import read_local
from application.qualification import _sanitize
from application.platform.supervision import _local_path
REV='3c7c04c7fd9ebd06a626756c7313c4c17168a4ec'
TARGET=REPO/'status/codex/productization/S12/runtime-identity-sharing-fix-source-20261008'
MANIFEST=TARGET.parent/'runtime-identity-sharing-fix-source-artifact-hashes-20261008.json'
FAILED=BASE/'r7-productization-S12-runtime-identity-qualified-3c7c04c'
LOGS=[f'{n:03d}-{phase}-{suite}.log' for n,phase,suite in [
(1,'phase_1','brokers'),(2,'phase_1','position'),(3,'phase_1','execution'),(4,'phase_1','execution'),(5,'phase_1','position'),(6,'phase_1','brokers'),(7,'phase_1','execution'),(8,'phase_1','position'),(9,'phase_1','storage'),(10,'phase_1','storage'),(11,'phase_1','storage'),(12,'phase_1','integration'),(13,'phase_1','integration'),(14,'phase_1','integration'),(15,'phase_1','safety'),(16,'phase_1','e2e'),(17,'phase_2','market_data'),(18,'phase_2','indicators'),(19,'phase_2','strategy'),(20,'phase_2','backtest'),(21,'phase_2','validation'),(22,'phase_2','execution'),(23,'phase_2','brokers'),(24,'phase_2','risk'),(25,'phase_2','position'),(26,'phase_2','storage'),(27,'phase_2','platform'),(28,'phase_2','integration'),(29,'phase_2','e2e'),(30,'phase_2','safety'),(31,'phase_2','application'),(32,'phase_2','product')]]

def main():
    _local_path(TARGET);_local_path(MANIFEST)
    assert not TARGET.exists() and not MANIFEST.exists()
    # All reads are a fixed local public allowlist, never paths selected by report JSON.
    sources={f'failed-source/{name}':FAILED/name for name in LOGS+['qualification.json','qualification-context.json','hardware-observations.json']}
    diag=BASE/'S12-runtime-identity-isolation-diagnostic-3c7c04c'
    for name in ['disposition.json','heartbeat.json','memory-fault-entered.json','memory-fault-result.json','outer.log','paper-result.json','timeout-fault-entered.json','workers.log']:sources[f'diagnostic/{name}']=diag/name
    sources['windows-sharing-reproduction.json']=BASE/'S12-runtime-identity-isolation-lock-reproduction-3c7c04c/disposition.json'
    for label in ['RED','GREEN','INTEGRATION']:
        for suffix in ['log','json']:
            name=f'S12-runtime-identity-isolation-{label}.{suffix}';sources[f'regression/{name}']=BASE/name
    for name in ['s12_runtime_identity_source_qualify.py','diagnose_s12_research_isolation.py','run_s12_isolation_regression.py','s12_runtime_identity_sharing_fixed_source_qualify.py',Path(__file__).name]:sources[f'tools/{name}']=BASE/name
    raw={name:read_local(path.parent,path.name,8*1024**2) for name,path in sources.items()}
    report=json.loads(raw['failed-source/qualification.json']);context=json.loads(raw['failed-source/qualification-context.json'])
    assert report['passed'] is False and report['tests_run']==1968 and len(report['commands'])==32
    assert sum(c['failures'] for c in report['commands'])==1 and sum(c['errors'] for c in report['commands'])==0
    assert report['source_before']==report['source_after']==dict(revision=REV,worktree='CLEAN')
    assert context['inputs_unchanged'] is True and len(context['source_input_hashes'])==617 and context['awake_request']['restored'] is True
    for command,name in zip(report['commands'],LOGS):
        assert command['log']==name and command['tree_reaped'] is True
        assert sha(raw[f'failed-source/{name}']).removeprefix('sha256:')==command['log_sha256']
    assert context['launcher_sha256']==sha(raw['tools/s12_runtime_identity_source_qualify.py'])
    assert sha(raw['tools/s12_runtime_identity_sharing_fixed_source_qualify.py'])=='sha256:9f86950cbaef71db56279010b498315275c1ca20104d928b62d5808df79ea8f5'
    samples=json.loads(raw['failed-source/hardware-observations.json'])['samples']
    assert len(samples)==508 and all(s['available_memory_bytes']>=s['existing_admission_minimum_bytes'] for s in samples)
    expected={'RED':1,'GREEN':0,'INTEGRATION':0}
    for label,code in expected.items():
        proof=json.loads(raw[f'regression/S12-runtime-identity-isolation-{label}.json'])
        assert proof['exit_code']==code and proof['tree_reaped'] is True and proof['inputs_unchanged'] is True and proof['awake_request']['restored'] is True
        assert proof['log_sha256']==sha(raw[f'regression/S12-runtime-identity-isolation-{label}.log'])
    reviewed={'tests/product/paper_worker_fixture.py':'a604049037a4201c53effe5fd34953cd86371a506b92ef89ad9085e7a4d6f9ab','tests/product/test_paper_worker_fixture_publish.py':'81a8a79f408786fe99ff83c093f96d35ba32dcc7724317abb973983ef808f13f'}
    for name,expected_hash in reviewed.items():assert sha(read_local((REPO/name).parent,(REPO/name).name,1024**2)).removeprefix('sha256:')==expected_hash
    review=dict(scope='BOUNDED_FIXTURE_SOURCE_AND_REGRESSIONS;FRESH_SOURCE_LAUNCHER_LITERAL_DIFF_ONLY',critical=0,important=0,reviewer='/root/qualification_review',reviewer_execution='NONE',source_hashes=reviewed,source_launcher_sha256='9f86950cbaef71db56279010b498315275c1ca20104d928b62d5808df79ea8f5')
    disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',failed_executable_revision=REV,failed_source=dict(commands=32,tests_run=1968,failures=1,errors=0,registry='NOT_RUN',qualification_credit='NONE'),original_child_trace='UNAVAILABLE_ORIGINAL_TEMPORARY_LOG_REMOVED',root_cause_status='DETERMINISTIC_WINDOWS_SHARING_RACE_REPRODUCED;COMPATIBLE_WITH_ORIGINAL_FAILURE_NOT_PROVEN_EXACT_CAUSE',diagnostic=dict(unchanged_isolation_case='1_PASS',sample_gaps_max_seconds=2.016529,memory_below_existing_admission=0),fixture_fix=dict(scope='ISOLATED_TEST_WORKER_ONLY',windows_error_codes=[5,32],retry_window_seconds=5,atomic_replace=True,observation_timeout_seconds=20,paper_owned_timeout_seconds=60,red=dict(tests=2,failures=2),green=dict(tests=3,failures=0),integration=dict(tests=4,failures=0)),new_candidate='REQUIRED;FRESH_EXACT_CLEAN_FULL_SOURCE_AND_SCOPED_NATIVE_NOT_YET_RUN',production_profile='PROPOSED_NOT_ACTIVE',ordinary_native_paper='NOT_RUN',real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',master_complete=False)
    raw['bounded-review.json']=(json.dumps(review,indent=2)+'\n').encode();raw['disposition.json']=(json.dumps(disposition,indent=2)+'\n').encode()
    assert len(raw)==57
    kept={name:_sanitize(value.decode('utf-8'),REPO).replace(str(BASE.parent),'<PROJECT_ROOT>').replace('\r\n','\n').encode() for name,value in raw.items()}
    # Recheck every captured public input before the first repository publication.
    assert all(read_local(path.parent,path.name,8*1024**2)==raw[name] for name,path in sources.items())
    TARGET.mkdir();files={}
    for name,value in kept.items():
        path=TARGET/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(value)
        assert path.read_bytes()==value;files[path.relative_to(REPO).as_posix()]=sha(value)
    manifest=dict(scope='FAILED_3C7_SOURCE_NO_QUALIFICATION_CREDIT_AND_ACTUAL_BOUNDED_FIXTURE_FIX',captured_at_utc=stamp(),files=files,count=len(files))
    with MANIFEST.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(retained=len(files),manifest=MANIFEST.relative_to(REPO).as_posix())),flush=True)
if __name__=='__main__':main()
