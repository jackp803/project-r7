"""Bounded actual E2/E4/E5/E6 journal growth on a controlled4h source clock.

Synthetic input, controlled native measurement boundary from existing source
integration fixture. No provider calls, elapsed/PQR/native qualification credit,
handwritten database rows or installed authorization. Retains measurements only.
"""
import argparse
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import time

from market_data.candle import Candle
from tests.product.test_paper_recorded_funding import PaperRecordedFundingTests
from tools.verify_public_archive_volume import peak_memory


def run(output,seconds):
    if output.exists() or not 10<=seconds<=300:raise ValueError('Fresh bounded journal diagnostic required')
    output.mkdir();case=PaperRecordedFundingTests();measurements=[];started=time.perf_counter()
    try:
        case.prepare(four_hour=True)
        event=case.event(0,bars=True)
        early=tuple(Candle('contracts-v0.1','BTC_USDT_PERP','4h',
            case.initial-timedelta(hours=(200-i)*4),case.initial-timedelta(hours=(199-i)*4),
            Decimal(58000+i),Decimal(58001+i),Decimal(57999+i),Decimal(58000+i),Decimal('1'),
            True,'CONTROLLED_GROWTH_ONLY',received_at=case.initial) for i in range(198))
        case.runtime.on_market_event(replace(event,candles=early+event.candles))
        for second in range(1,seconds+1):
            case.clock[0]=case.initial+timedelta(seconds=second)
            if second%30==0:case.observe(case.clock[0])
            began=time.perf_counter()
            if second%5==1:case.runtime.on_market_event(case.event(second))
            case.runtime.on_deadline(case.clock[0])
            duration=time.perf_counter()-began
            if second in (1,10,25,50,100,seconds):
                db=case.service.process._db
                row=db.execute('SELECT count(*),coalesce(sum(length(CAST(state_json AS BLOB))),0) FROM paper_process_checkpoints WHERE run_id=?',(case.ref.run_id,)).fetchone()
                effects=db.execute('SELECT count(*),coalesce(sum(length(CAST(outcome_json AS BLOB))),0) FROM paper_process_effects WHERE run_id=?',(case.ref.run_id,)).fetchone()
                current=case.service.process.recover(case.ref.run_id)
                item=dict(controlled_seconds=second,operations=current.revision,checkpoint_rows=row[0],
                    retained_checkpoint_text_bytes=row[1],effect_rows=effects[0],retained_effect_text_bytes=effects[1],
                    last_tick_wall_seconds=duration,sqlite_main_bytes=case.config.database_path.stat().st_size,
                    state_bytes=len(current.state_json.encode()),cached4h_bars=len(current.state['runtime']['candles']['4h']))
                measurements.append(item);print(json.dumps(item),flush=True)
        last=measurements[-1]
        profile=case.service.simulation.as_dict()
        result=dict(status='BOUNDED_CONTROLLED_ACTUAL_JOURNAL_DIAGNOSTIC_NOT_CAPACITY_PASS',
            actual_provider_requests=0,actual_provider_responses=0,elapsed_forward_credit='NONE',
            namespace='LOCAL_RESEARCH',native_boundary='CONTROLLED_UNIT_MEASUREMENT_NOT_NATIVE_PASS',
            strategy_timeframe='4h',cache_policy_limit=profile['maximum_cached_candles_per_timeframe'],
            measurements=measurements,base30day_deadline_plus_market_operations=3110400,
            projected30day_checkpoint_text_bytes=last['retained_checkpoint_text_bytes']*3110400//last['operations'],
            projection='SAMPLE_MEAN_CHECKPOINT_TEXT_ONLY;EXCLUDES_INDEXES_CANONICAL_GRAPH_REQUESTS_EFFECTS_FUTURE_GROWTH',
            source_hashes={p:'sha256:'+hashlib.sha256((Path(__file__).parents[1]/p).read_bytes()).hexdigest() for p in
                ('src/storage/paper_process.py','src/application/paper/engine.py','tools/measure_paper_journal_growth.py')},
            wall_seconds=time.perf_counter()-started,**peak_memory())
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(json.dumps(result),flush=True)
    finally:case.doCleanups()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=100);args=parser.parse_args();run(args.output.absolute(),args.seconds)
