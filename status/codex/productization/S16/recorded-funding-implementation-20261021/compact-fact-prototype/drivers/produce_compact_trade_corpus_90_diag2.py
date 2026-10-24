"""Finite actual source E2/E4/E5/E6 corpus: growing closed trades + protected head.

Sparse controlled4h boundaries, NOT declared1s/5s30day or real-time acceptance.
No source DB rows injected, native/market/clock boundary is existing source QA.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
import ctypes,hashlib,json,sqlite3,tempfile,time
from market_data.candle import Candle
from tests.product import test_paper_recorded_funding as recorded
from tests.product.test_paper_encoded_checkpoint_consumers import EncodedRecordedFundingRegressionTests
from tools.verify_public_archive_volume import peak_memory

art=Path(__file__).parent;output=art/'compact-ninety-trade-corpus-diag2-20261024'
if output.exists():raise RuntimeError('Fresh actual source diagnostic required')
output.mkdir();temp=Path.cwd().parents[1]/'qa'/'cfc90diag2';temp.mkdir(parents=True);tempfile.tempdir=str(temp)
case=EncodedRecordedFundingRegressionTests();started=time.perf_counter();cpu=time.process_time();samples=[];durations=[]
names=('src/application/paper/engine.py','src/application/paper/service.py','src/storage/paper_process.py','src/storage/paper_state_codec.py')
hashes={name:'sha256:'+hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in names}
def step(event,expected):
    began=time.perf_counter();outcome=case.runtime.on_market_event(event);durations.append(time.perf_counter()-began)
    if outcome.status!=expected:raise RuntimeError('SOURCE_FLOW_REFUSED:'+outcome.status+':'+str(outcome.reason_codes))
def event(second,price,bars=()):return replace(case.event(second,price=str(price)),candles=tuple(bars))
def candles(start,count,price):
    rows=[]
    for i in range(count):
        at=start+timedelta(hours=4*i);close=Decimal(price)+Decimal(100*i)
        rows.append(Candle('contracts-v0.1','BTC_USDT_PERP','4h',at-timedelta(hours=4),at,close-20,close+1,close-21,close,Decimal(1),
            True,'CONTROLLED_GROWTH_CORPUS_ONLY',received_at=case.clock[0]))
    return rows
def sample(trades):
    current=case.service.process.management_snapshot(case.ref.run_id);db=case.service.process._db
    value=dict(closed_trades=len(current.state['runtime']['closed_trades']),requested_completed=trades,revision=current.revision,
        logical_state_bytes=len(current.state_json.encode()),cached4h_bars=len(current.state['runtime']['candles']['4h']),
        sqlite_bytes=db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0],
        wall_seconds=time.perf_counter()-started,**peak_memory())
    samples.append(value);print(json.dumps(value),flush=True)
try:
    if not ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):raise ctypes.WinError()
    original_policy=recorded.recorded_policy
    with patch.object(recorded,'recorded_policy',side_effect=lambda:dict(original_policy(),maximum_cached_candles_per_timeframe=256)):
        case.prepare(four_hour=True,instance_id='compact-ninety-trade-corpus-diag2-source-only')
    original_entry=case.service.entry_current
    def traced_entry(run_id):
        try:allowed=original_entry(run_id)
        except Exception as error:
            print(json.dumps(dict(entry_exception=type(error).__name__,reason=str(error))),flush=True);raise
        if not allowed:
            from dataclasses import asdict
            record=dict(status='ACTUAL_RELEASE_DENIED_NO_OVERRIDE',virtual_offset_seconds=(case.clock[0]-case.initial).total_seconds(),
                supervisor_failed=case.supervisor.failed,supervisor_failure_code=case.supervisor.failure_code,health=case.supervisor.health())
            try:
                current=case.selected.current();gate=case.service.registry.accepted_paper_start_evidence(case.identity)
                left=json.loads(gate.release_json);right=asdict(current)
                record['different_release_fields']={key:dict(original=left.get(key),current=right.get(key)) for key in left if key!='runtime_generation' and left.get(key)!=right.get(key)}
            except Exception as error:
                chain=[]
                while error is not None:
                    chain.append(dict(type=type(error).__name__,reason=str(error)));error=error.__cause__
                record['release_error_chain']=chain
            (output/'release-denial.json').write_text(json.dumps(record,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
            print(json.dumps(record,default=str),flush=True)
        return allowed
    case.service.entry_current=traced_entry
    first=case.event(0,bars=True)
    early=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','4h',case.initial-timedelta(hours=(256-i)*4),
        case.initial-timedelta(hours=(255-i)*4),Decimal(58000+i),Decimal(58001+i),Decimal(57999+i),Decimal(58000+i),Decimal(1),
        True,'CONTROLLED_GROWTH_CORPUS_ONLY',received_at=case.initial) for i in range(254))
    step(replace(first,candles=early+first.candles),'ACKNOWLEDGED')
    step(event(1,60000),'PROTECTED');step(event(2,60020),'EXIT_REQUESTED');step(event(3,60020),'FUNDING_PENDING')
    for number in range(1,91):
        if time.perf_counter()-started>270:raise RuntimeError('FINITE_SOURCE_CORPUS_DEADLINE_NO_SCOPE_EXPANSION')
        offset=number*8*3600;price=60000+200*number;case.clock[0]=case.initial+timedelta(seconds=offset);case.observe(case.clock[0])
        rows=candles(case.clock[0]-timedelta(hours=4),2,price-100)
        step(event(offset,price,rows),'CLOSED')
        if number in (1,5,10,20,30,60,90):sample(number)
        step(event(offset+1,price),'ACKNOWLEDGED');step(event(offset+2,price),'PROTECTED')
        if number<90:
            step(event(offset+3,price+20),'EXIT_REQUESTED');step(event(offset+4,price+20),'FUNDING_PENDING')
    current=case.service.process.management_snapshot(case.ref.run_id)
    if len(current.state['runtime']['closed_trades'])!=90 or current.state['runtime']['position']['lifecycle_state']!='OPEN_PROTECTED':raise RuntimeError('Actual completed history and protected head required')
    target=output/'controlled-source-snapshot.sqlite'
    with sqlite3.connect(target) as destination:case.service.process._db.backup(destination)
    if hashes!={name:'sha256:'+hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in names}:raise RuntimeError('Source changed during corpus generation')
    result=dict(status='ACTUAL_SOURCE_90_CLOSED_PLUS_PROTECTED_HEAD_SPARSE_DIAGNOSTIC_NOT30DAY_VOLUME_OR_NATIVE',
        source_hashes=hashes,samples=samples,closed_trades=90,current_revision=current.revision,
        current_state_bytes=len(current.state_json.encode()),position=current.state['runtime']['position']['lifecycle_state'],
        snapshot_sha256='sha256:'+hashlib.sha256(target.read_bytes()).hexdigest(),
        workload='SPARSE8H_BOUNDARIES_AND_ACTUAL_INTERMEDIATE_ENTRY_PROTECTION_EXIT_FUNDING_OWNER_OPERATIONS;NOT1S5S',
        financial_policy='EXISTING_SOURCE_FIXTURE_NOT_SELECTED_HUMAN_FEES_OR_RISK_QUALIFICATION',
        maximum_observed_source_operation_seconds=max(durations),actual_provider_requests=0,elapsed_credit='NONE',native='NOT_QUALIFIED',
        wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time()-cpu,**peak_memory())
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result),flush=True)
finally:case.doCleanups();ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
