from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import hashlib,json,time
from pathlib import Path
from market_data.candle import Candle
from tests.product.test_paper_encoded_checkpoint_consumers import EncodedRecordedFundingRegressionTests
from tools.verify_public_archive_volume import peak_memory

output=Path(__file__).parent/'e6-owned-cached-growth-20261024'
if output.exists():raise RuntimeError('Fresh measurement required')
output.mkdir();case=EncodedRecordedFundingRegressionTests();measurements=[];started=time.perf_counter()
try:
    case.prepare(four_hour=True,instance_id='encoded-growth-20261024')
    event=case.event(0,bars=True)
    early=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','4h',
        case.initial-timedelta(hours=(200-i)*4),case.initial-timedelta(hours=(199-i)*4),
        Decimal(58000+i),Decimal(58001+i),Decimal(57999+i),Decimal(58000+i),Decimal('1'),
        True,'CONTROLLED_ENCODED_GROWTH_ONLY',received_at=case.initial) for i in range(198))
    case.runtime.on_market_event(replace(event,candles=early+event.candles))
    for second in range(1,101):
        case.clock[0]=case.initial+timedelta(seconds=second)
        if second%30==0:case.observe(case.clock[0])
        began=time.perf_counter()
        if second%5==1:case.runtime.on_market_event(case.event(second))
        case.runtime.on_deadline(case.clock[0])
        duration=time.perf_counter()-began
        if second in (1,10,25,50,100):
            db=case.service.process._db;current=case.service.process.management_snapshot(case.ref.run_id)
            counts={table:tuple(db.execute('SELECT count(*),coalesce(sum(length(CAST('+column+' AS BLOB))),0) FROM '+table+' WHERE run_id=?',(case.ref.run_id,)).fetchone())
                for table,column in [('paper_process_checkpoints','state_json'),('paper_process_effects','outcome_json'),('paper_process_operations','request_json')]}
            row=dict(controlled_seconds=second,operations=current.revision,last_tick_wall_seconds=duration,
                state_bytes=len(current.state_json.encode()),cached4h_bars=len(current.state['runtime']['candles']['4h']),
                counts=counts,sqlite_main_bytes=case.config.database_path.stat().st_size,
                history_ready=case.service.history_ready(case.ref.run_id))
            measurements.append(row);print(json.dumps(row),flush=True)
    result=dict(status='CONTROLLED_ENCODED_CURRENT_GROWTH_DIAGNOSTIC_NOT_CAPACITY_PASS',actual_provider_requests=0,
        native='CONTROLLED_SOURCE_FIXTURE_NOT_NATIVE',elapsed_credit='NONE',measurements=measurements,
        wall_seconds=time.perf_counter()-started,**peak_memory(),
        source_hashes={name:'sha256:'+hashlib.sha256((Path.cwd()/name).read_bytes()).hexdigest() for name in
            ('src/storage/paper_process.py','src/storage/paper_history_audit.py','src/application/paper/service.py','src/application/paper/engine.py')})
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result),flush=True)
finally:case.doCleanups()
