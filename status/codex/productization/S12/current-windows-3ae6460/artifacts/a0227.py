"""Recover already produced public metadata; never reexecute successful flows."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.platform.private_files import create_private_directory,require_private,write_private_new
from application.qualification import revision_fact
REV='3ae6460c69a8a8f90588c396b819af7079e7546d'
revision_fact(ROOT,REV,True)
original=BASE/'b03-m04-f11-temporary-awake-3ae6460.json'
raw=original.read_bytes();observed=json.loads(raw)
proof_path=BASE/'b03-m04-f11-3ae6460-first/supplemental-assertions.json'
proof_raw=proof_path.read_bytes();proof=json.loads(proof_raw)
assert observed['passed'] is True and observed['exit_code']==0 and observed['awake']['restored'] is True
assert observed['helper_unchanged'] is True and observed['source_unchanged'] is True
assert proof['passed'] is True and proof['errors']==[] and proof['cleanup_errors']==[]
assert {row['requirement_id']:row['status'] for row in proof['records']}==dict(B03='PASS',M04='PASS',F11='PASS')
assert proof['helper_hash']=='sha256:'+observed['helper_sha256']
target=BASE/'b03-m04-f11-awake-records-3ae6460'
create_private_directory(target)
write_private_new(target/'original-observation.json',raw)
require_private(target/'original-observation.json')
assert (target/'original-observation.json').read_bytes()==raw
result=dict(revision=REV,scope='METADATA_ARCHIVAL_RECOVERY_ONLY;NO_REEXECUTION',
    original_outer_exit_code=1,original_outer_archival_status='FAILED_OWNER_PRIVATE_PERMISSIONS_REQUIRED',
    original_observation_ref=original.relative_to(PROJECT).as_posix(),
    original_observation_sha256=hashlib.sha256(raw).hexdigest(),
    original_passed_field_scope='HELPER_COMPLETED_AND_AWAKE_RELEASED_BEFORE_FAILED_ARCHIVAL_ASSERTION;NOT_OUTER_ARCHIVAL_SUCCESS',
    original_wrapper_ref='run_b03_m04_f11_awake_before_private_record.py',
    original_wrapper_sha256=hashlib.sha256((BASE/'run_b03_m04_f11_awake_before_private_record.py').read_bytes()).hexdigest(),
    repaired_wrapper_ref='run_b03_m04_f11_awake.py',
    repaired_wrapper_sha256=hashlib.sha256((BASE/'run_b03_m04_f11_awake.py').read_bytes()).hexdigest(),
    original_actual_supplement_sha256=hashlib.sha256(proof_raw).hexdigest(),
    original_actual_helper_interval=[proof['started_at_utc'],proof['finished_at_utc']],
    actual_b03_m04_f11='PASS',actual_awake_restored=True,private_copy_verified=True,
    repeat_execution=False,provider_requests=0,credentials='NONE',capital='NONE',
    product_security_policy='UNCHANGED;PRIVATE_WRITER_NOT_RELAXED')
revision_fact(ROOT,REV,True)
write_private_new(target/'recovery.json',(json.dumps(result,indent=2)+'\n').encode())
print(json.dumps(result),flush=True)
