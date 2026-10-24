"""Actual controlled owner workload; projections never establish30day PASS."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import ctypes,hashlib,json,sqlite3,statistics,time
from market_data.candle import Candle
from tests.product.test_paper_encoded_checkpoint_consumers import EncodedRecordedFundingRegressionTests
from tools.verify_public_archive_volume import peak_memory

root=Path.cwd();output=Path(__file__).parent/'e6-3600second-growth-20261024'
if output.exists():raise RuntimeError('Fresh diagnostic path required')
output.mkdir();case=EncodedRecordedFundingRegressionTests();samples=[];ticks=[];started=time.perf_counter();cpu=time.process_time()
names=('src/storage/paper_process.py','src/storage/paper_state_codec.py','src/storage/paper_history_audit.py',
       'src/application/paper/service.py','src/application/paper/engine.py')
hashes={name:'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}

def snapshot(second,duration):
    db=case.service.process._db;current=case.service.process.management_snapshot(case.ref.run_id)
    inventories={}
    for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        name=row[0];quoted='"'+name.replace('"','""')+'"'
        text=[c[1] for c in db.execute('PRAGMA table_info('+quoted+')') if c[2].upper()=='TEXT']
        expression='+'.join('coalesce(length(CAST("'+c.replace('"','""')+'" AS BLOB)),0)' for c in text) or '0'
        count,size=db.execute('SELECT count(*),coalesce(sum('+expression+'),0) FROM '+quoted).fetchone()
        if count:inventories[name]=dict(rows=count,text_bytes=size)
    total=case.config.database_path.stat().st_size
    wal=Path(str(case.config.database_path)+'-wal');wal_bytes=wal.stat().st_size if wal.exists() else 0
    item=dict(controlled_second=second,revision=current.revision,sqlite_main_bytes=total,wal_bytes=wal_bytes,
        sqlite_allocated_bytes=db.execute('PRAGMA page_size').fetchone()[0]*db.execute('PRAGMA page_count').fetchone()[0],
        logical_state_bytes=len(current.state_json.encode()),position_state=current.state['runtime']['position']['lifecycle_state'],
        cached4h_bars=len(current.state['runtime']['candles']['4h']),last_tick_seconds=duration,
        inventories=inventories,wall_seconds=time.perf_counter()-started,**peak_memory())
    samples.append(item);(output/'progress.json').write_text(json.dumps(item,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in item.items() if k!='inventories'}),flush=True)

try:
    if not ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):raise ctypes.WinError()
    case.prepare(four_hour=True,instance_id='e6-3600second-growth-20261024')
    event=case.event(0,bars=True)
    early=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','4h',case.initial-timedelta(hours=(256-i)*4),
        case.initial-timedelta(hours=(255-i)*4),Decimal(58000+i),Decimal(58001+i),Decimal(57999+i),
        Decimal(58000+i),Decimal(1),True,'CONTROLLED_CAPACITY_ONLY',received_at=case.initial) for i in range(254))
    entry=case.runtime.on_market_event(replace(event,candles=early+event.candles))
    if entry.status!='ACKNOWLEDGED':raise RuntimeError('Actual owner entry refused: '+str(entry.reason_codes))
    snapshot(0,0)
    for second in range(1,3601):
        case.clock[0]=case.initial+timedelta(seconds=second)
        if second%30==0:case.observe(case.clock[0])
        began=time.perf_counter()
        if second%5==1:case.runtime.on_market_event(case.event(second))
        case.runtime.on_deadline(case.clock[0]);duration=time.perf_counter()-began;ticks.append(duration)
        if second in (1,100,300,600,1200,1800,2400,3000,3600):snapshot(second,duration)
    # Consistent actual source snapshot, never runtime permission/configuration.
    target=output/'controlled-source-snapshot.sqlite'
    with sqlite3.connect(target) as destination:case.service.process._db.backup(destination)
    if hashes!={name:'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}:raise RuntimeError('Source changed during diagnostic')
    last=samples[-1];base=samples[0];operations=last['revision']-base['revision'];target_operations=3110400
    result=dict(status='ACTUAL_CONTROLLED_3600SECOND_WORKLOAD_NOT30DAY_OR_NATIVE_PASS',source_hashes=hashes,
        samples=samples,ticks=len(ticks),maximum_tick_seconds=max(ticks),p95_tick_seconds=sorted(ticks)[int(.95*(len(ticks)-1))],
        median_tick_seconds=statistics.median(ticks),ticks_over_one_second=sum(t>1 for t in ticks),
        measured_operations=operations,projection_operations_30day=target_operations,
        projected30day_sqlite_growth_bytes=(last['sqlite_allocated_bytes']-base['sqlite_allocated_bytes'])*target_operations//operations,
        projection_scope='ACTUAL_SAMPLE_GROWTH_ONLY;NOT_GENERATED_30DAY_NOT_FUTURE_STATE_OR_TRADE_BOUND',
        snapshot_sha256='sha256:'+hashlib.sha256(target.read_bytes()).hexdigest(),
        actual_provider_requests=0,elapsed_credit='NONE',native='NOT_QUALIFIED',
        selected_policy='NOT_CLAIMED;EXISTING_OWNER_FIXTURE_POLICY',wall_seconds=time.perf_counter()-started,
        cpu_seconds=time.process_time()-cpu,**peak_memory())
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'}),flush=True)
finally:
    case.doCleanups();ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
