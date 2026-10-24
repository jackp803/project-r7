"""Normal private backup/restore of actual source-produced pending Paper facts.

Controlled source/policy/native and restore clock, not native commissioning.
No copied authorization into ordinary profile, no database rows hand-written.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import ctypes,hashlib,json,tempfile,time
from tests.product.test_paper_encoded_checkpoint_consumers import EncodedRecordedFundingRegressionTests
from application.config import load_config
from application.platform.product_backup import create_product_backup,verify_product_backup,restore_product_backup
from application.platform.restoration import require_valid_restoration
from storage.paper_process import open_paper_process_journal
from tools.verify_public_archive_volume import peak_memory

output=Path(__file__).parent/'e6-pending-product-backup-20261024'
if output.exists():raise RuntimeError('Fresh output required')
output.mkdir();work=output/'qa-temporary';work.mkdir();tempfile.tempdir=str(work)
case=EncodedRecordedFundingRegressionTests();result=dict(protocol='ACTUAL_SOURCE_OWNER_NORMAL_PRIVATE_BACKUP_CONTROLLED_BOUNDARIES',
    actual_public_requests=0,actual_private_requests=0,elapsed_credit='NONE',native='NOT_QUALIFIED',phases=[])
started=time.perf_counter()
def phase(name,producer):
    began=time.perf_counter()
    try:
        facts=producer();result['phases'].append(dict(phase=name,status='PASS',wall_seconds=time.perf_counter()-began,facts=facts));return facts
    except Exception as error:
        result['phases'].append(dict(phase=name,status='FAIL',wall_seconds=time.perf_counter()-began,error_type=type(error).__name__,reason=str(error)));raise
try:
    if not ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):raise ctypes.WinError()
    case.close_pending(instance_id='encoded-pending-backup-20261024')
    before=case.service.process.management_snapshot(case.ref.run_id)
    if before.state['runtime']['pending_funding'] is None:raise RuntimeError('Actual flat pending work required')
    source_binding=before.binding_json;source_state=before.state_json;run=case.ref.run_id;generation=before.process_generation
    result['source']=dict(run_id=run,revision=before.revision,generation=generation,
        state_sha256='sha256:'+hashlib.sha256(source_state.encode()).hexdigest(),position=before.state['runtime']['position']['lifecycle_state'],
        financial_status='PENDING_FUNDING_NO_FINAL_SAMPLE',selected_policy='EXISTING_CONTROLLED_FIXTURE_NOT_HUMAN_POLICY')
    # Close actual context managers in LIFO order, retaining only the helper's
    # final temp/patch cleanup. Product backup acquires original stopped scopes.
    while len(case._cleanups)>1:
        function,args,kwargs=case._cleanups.pop();function(*args,**kwargs)
    phase('CREATE_FULL_PRODUCT_BACKUP',lambda:create_product_backup(case.config,output/'backup',timeout_seconds=300))
    phase('INDEPENDENT_VERIFY',lambda:verify_product_backup(case.config,output/'backup',timeout_seconds=300))
    # The existing source fixture intentionally runs one hour ahead. Match its
    # restore clock explicitly; never change stored clocks or product guards.
    at=case.clock[0]+timedelta(seconds=1)
    class RestoreClock(datetime):
        @classmethod
        def now(cls,tz=None):return at.astimezone(tz) if tz is not None else at.replace(tzinfo=None)
    with patch('application.platform.database_restore.datetime',RestoreClock):
        phase('RESTORE_NORMAL_PRODUCT',lambda:restore_product_backup(case.config,output/'backup',output/'restored',timeout_seconds=300))
    restored=load_config(output/'restored/restored-product.json');marker=require_valid_restoration(restored)
    with open_paper_process_journal(restored.database_path) as journal:
        actual=journal.audit_full(run)
        if actual.state_json!=source_state or actual.binding_json!=source_binding:raise RuntimeError('Restored original exact state/binding changed')
        if actual.process_generation!=generation+1:raise RuntimeError('Restored generation not fenced')
        if journal.history_audit_ready(run):raise RuntimeError('Restored private proof was imported')
    if marker['status']!='RESTORED_INHIBITED' or restored.cloud_root is not None or restored.paper_runtime_enabled:raise RuntimeError('Restored profile gained runtime authority')
    result['restored']=dict(status=marker['status'],generation=actual.process_generation,exact_original_bytes=True,
        pending_funding_retained=True,history_proof_imported=False,cloud_connected=False,paper_runtime_enabled=False,
        reconciliation='REQUIRED',reauthorization='REQUIRED',restore_clock='EXPLICIT_CONTROLLED_SOURCE_CLOCK_NOT_NATIVE_WALL_CLOCK')
    result['status']='SOURCE_POPULATED_ENCODED_PENDING_PRODUCT_BACKUP_VERIFY_RESTORE_PASS_NOT_NATIVE_OR_CAPACITY'
except Exception:
    result['status']='SOURCE_POPULATED_BACKUP_CHECK_INCOMPLETE';raise
finally:
    case.doCleanups();ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    result.update(wall_seconds=time.perf_counter()-started,**peak_memory())
    (output/'result.json').write_text(json.dumps(result,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,default=str),flush=True)
