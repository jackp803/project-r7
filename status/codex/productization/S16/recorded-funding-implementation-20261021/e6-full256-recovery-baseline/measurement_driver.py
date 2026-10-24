"""Controlled actual E2/E4/E5/E6 resource diagnostic; no native/elapsed credit."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import hashlib,json,sqlite3,statistics,time
from pathlib import Path
from market_data.candle import Candle
from storage.runtime_models import RuntimeConflictError
from tests.product.test_paper_encoded_checkpoint_consumers import EncodedRecordedFundingRegressionTests
from tools.verify_public_archive_volume import peak_memory

root=Path.cwd();output=Path(__file__).parent/'e6-256bar-recovery-20261024'
if output.exists():raise RuntimeError('Fresh bounded output required')
output.mkdir();case=EncodedRecordedFundingRegressionTests();samples=[];times=[];recovery={};started=time.perf_counter()
source_names=('src/storage/paper_process.py','src/storage/paper_history_audit.py','src/storage/paper_history_worker.py',
    'src/application/paper/service.py','src/application/paper/engine.py')
source_hashes={name:'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest() for name in source_names}
def sample(second,duration):
    journal=case.service.process;db=journal._db;current=journal.management_snapshot(case.ref.run_id)
    physical=db.execute('SELECT state_json FROM paper_process_checkpoints WHERE run_id=? AND revision=?',(case.ref.run_id,current.revision)).fetchone()[0]
    value=dict(controlled_second=second,revision=current.revision,physical_kind=json.loads(physical)['kind'],
        management_tick_seconds=duration,state_bytes=len(current.state_json.encode()),
        cached4h_bars=len(current.state['runtime']['candles']['4h']),position=current.state['runtime']['position']['lifecycle_state'],
        history_ready=case.service.history_ready(case.ref.run_id),sqlite_main_bytes=case.config.database_path.stat().st_size)
    samples.append(value);print(json.dumps(value),flush=True)
try:
    case.prepare(four_hour=True,instance_id='e6-256bar-recovery-20261024')
    event=case.event(0,bars=True)
    early=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','4h',
        case.initial-timedelta(hours=(256-i)*4),case.initial-timedelta(hours=(255-i)*4),
        Decimal(58000+i),Decimal(58001+i),Decimal(57999+i),Decimal(58000+i),Decimal('1'),
        True,'CONTROLLED_CAPACITY_ONLY',received_at=case.initial) for i in range(254))
    if case.runtime.on_market_event(replace(event,candles=early+event.candles)).status!='ACKNOWLEDGED':
        raise RuntimeError('Actual E2/E5 owner entry required for held-position workload')
    second=0
    for second in range(1,301):
        case.clock[0]=case.initial+timedelta(seconds=second)
        if second%30==0:case.observe(case.clock[0])
        if second==201:
            old_runtime=case.runtime;before=case.service.process.management_snapshot(case.ref.run_id)
            began=time.perf_counter();successor=case.enterContext(case.selected.owners.service())
            runtime=successor.runtime(case.ref.run_id)
            recovery['attachment_wall_seconds']=time.perf_counter()-began
            recovery['original_position_id']=before.state['runtime']['position']['position_id']
            recovery['old_generation']=old_runtime.coordinator.generation;recovery['new_generation']=runtime.coordinator.generation
            recovery['new_owner_initially_history_ready']=successor.history_ready(case.ref.run_id)
            try:old_runtime.on_deadline(case.clock[0])
            except RuntimeConflictError:recovery['old_owner_fenced']=True
            else:raise RuntimeError('Actual stale owner was not fenced')
            case.service=successor;case.runtime=runtime
            began=time.perf_counter();runtime.on_deadline(case.clock[0])
            recovery['first_management_tick_wall_seconds']=time.perf_counter()-began
            current=successor.process.management_snapshot(case.ref.run_id)
            recovery['same_position_id']=current.state['runtime']['position']['position_id']==recovery['original_position_id']
            recovery['position_lifecycle']=current.state['runtime']['position']['lifecycle_state']
            recovery['no_healthy_credit_before_audit']=not current.state['runtime']['forward']['last_healthy']
            successor.history_audit_after_protection((case.ref.run_id,));recovery['audit_started_at_wall']=time.perf_counter()-started
        began=time.perf_counter()
        if second%5==1:case.runtime.on_market_event(case.event(second))
        case.runtime.on_deadline(case.clock[0]);duration=time.perf_counter()-began;times.append(duration)
        case.service.history_audit_after_protection((case.ref.run_id,))
        if second in (1,25,50,100,105,106,107,127,128,129,200,201,202,210,220,256,300):sample(second,duration)
    audit_wait_started=time.perf_counter()
    while not case.service.history_ready(case.ref.run_id) and time.perf_counter()-audit_wait_started<310:
        case.service.history_audit_after_protection((case.ref.run_id,))
        progress=case.service.process.history_audit_progress(case.ref.run_id)
        if progress.status=='HISTORY_AUDIT_FAILED':break
        second+=1;case.clock[0]=case.initial+timedelta(seconds=second)
        if second%30==0:case.observe(case.clock[0])
        began=time.perf_counter()
        if second%5==1:case.runtime.on_market_event(case.event(second))
        case.runtime.on_deadline(case.clock[0]);times.append(time.perf_counter()-began)
        time.sleep(.01)
    recovery['final_history_status']=case.service.process.history_audit_progress(case.ref.run_id).status
    recovery['audit_wait_wall_seconds']=time.perf_counter()-audit_wait_started
    recovery['total_recovery_to_observation_wall_seconds']=time.perf_counter()-started-recovery['audit_started_at_wall']
    journal=case.service.process;db=journal._db
    inventory={table:dict(rows=count) for table,count in db.execute("SELECT name,0 FROM sqlite_master WHERE type='table'")}
    for table in inventory:inventory[table]['rows']=db.execute('SELECT count(*) FROM "'+table.replace('"','""')+'"').fetchone()[0]
    with sqlite3.connect(output/'controlled-source-snapshot.sqlite') as destination:db.backup(destination)
    actual_keys={row['revision'] for row in db.execute('SELECT revision FROM paper_process_checkpoints WHERE run_id=?',(case.ref.run_id,))
        if row['revision']%128==0}
    for revision in actual_keys:
        physical=db.execute('SELECT state_json FROM paper_process_checkpoints WHERE run_id=? AND revision=?',(case.ref.run_id,revision)).fetchone()[0]
        if json.loads(physical)['kind']!='KEYFRAME':raise RuntimeError('Actual fixed keyframe boundary missing')
    ordered=sorted(times)
    result=dict(status='CONTROLLED_FULL256_KEYFRAME_SUCCESSOR_DIAGNOSTIC_NOT30DAY_OR_NATIVE_PASS',
        source_hashes=source_hashes,samples=samples,recovery=recovery,actual_keyframe_revisions=sorted(actual_keys),
        ticks=len(times),maximum_tick_seconds=max(times),p95_tick_seconds=ordered[int((len(ordered)-1)*.95)],
        median_tick_seconds=statistics.median(times),ticks_over_one_second=sum(value>1 for value in times),
        inventory=inventory,controlled_snapshot_sha256='sha256:'+hashlib.sha256((output/'controlled-source-snapshot.sqlite').read_bytes()).hexdigest(),
        snapshot='SQLITE_CONSISTENT_BACKUP_DIAGNOSTIC_ONLY_NO_CONFIG_AUTH_OR_PERMISSION',
        actual_provider_requests=0,elapsed_credit='NONE',native_boundary='CONTROLLED_SOURCE_FIXTURE_NOT_NATIVE',
        selected_human_policy='NOT_CLAIMED;EXISTING_OWNER_FIXTURE_POLICY',wall_seconds=time.perf_counter()-started,**peak_memory())
    if {name:'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest() for name in source_names}!=source_hashes:
        raise RuntimeError('Source changed during resource diagnostic')
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result),flush=True)
finally:case.doCleanups()
