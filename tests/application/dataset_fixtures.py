"""Synthetic Parquet inputs, never deployment data or financial defaults."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

START=datetime(2026,10,2,tzinfo=timezone.utc)

def z(value): return value.isoformat().replace('+00:00','Z')
def encoded(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def hashed(value): return 'sha256:'+hashlib.sha256(value).hexdigest()

def candle_schema():
    return pa.schema([pa.field(name,kind,nullable=nullable) for name,kind,nullable in [
        ('schema_version',pa.string(),False),('symbol',pa.string(),False),('timeframe',pa.string(),False),
        ('open_time',pa.timestamp('ms',tz='UTC'),False),('close_time',pa.timestamp('ms',tz='UTC'),False),
        *[(key,pa.string(),False) for key in ('open','high','low','close','volume')],
        ('is_closed',pa.bool_(),False),('source',pa.string(),False),
        ('received_at',pa.timestamp('ms',tz='UTC'),True),('source_record_id',pa.string(),True)]])

def logical_rows(rows):
    records=[]
    for row in rows:
        record=dict(row)
        for key in ('open_time','close_time','received_at'):
            if record[key] is not None: record[key]=z(record[key])
        # Literal inputs in this fixture use canonical integer decimal text.
        records.append(record)
    return hashed(encoded(records))

def dataset(root,*,compression='NONE',row_group_size=4,mutate=None,count=12):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i in range(count):
        lower=START+timedelta(hours=i); upper=lower+timedelta(hours=1)
        rows.append(dict(schema_version='contracts-v0.1',symbol='BTC_USDT_PERP',timeframe='1h',
                         open_time=lower,close_time=upper,open=str(100+i),high=str(102+i),
                         low=str(99+i),close=str(101+i),volume='10',is_closed=True,
                         source='SYNTHETIC_FIXTURE',received_at=upper,source_record_id='fixture-'+str(i)))
    if mutate: mutate(rows)
    target=root/'candles.parquet'
    pq.write_table(pa.Table.from_pylist(rows,schema=candle_schema()),target,compression=compression,row_group_size=row_group_size)
    funding=[dict(event_at=START+timedelta(hours=i),rate='0.0001',source='SYNTHETIC_FIXTURE') for i in range(0,count,8)]
    fs=pa.schema([pa.field('event_at',pa.timestamp('ms',tz='UTC'),False),pa.field('rate',pa.string(),False),pa.field('source',pa.string(),False)])
    pq.write_table(pa.Table.from_pylist(funding,schema=fs),root/'funding.parquet',compression=compression)
    funding_material=[dict(event_at=z(item['event_at']),rate=item['rate'],source=item['source']) for item in funding]
    manifest=dict(schema_version='r7-dataset-v0.2',dataset_id='fixture-dataset',dataset_version='1',
                  namespace='FIXTURE',symbol='BTC_USDT_PERP',source_instrument='SYNTHETIC:BTC-USDT',
                  normalization_version='r7-canonical-e1-v0.2',alignment='UTC',
                  availability_model='recorded_received_at',information_cutoff=z(START+timedelta(hours=count)),
                  units=dict(price='USDT_PER_BASE',volume='BASE',quantity='BASE',settlement='USDT',instrument_type='LINEAR_PERPETUAL'),
                  candles=[dict(path='candles.parquet',timeframe='1h',start=z(START),end=z(START+timedelta(hours=count)),
                                rows=count,finalized_rows=count,missing_ranges=[],duplicate_ranges=[],
                                logical_hash=logical_rows(rows),byte_hash=hashed(target.read_bytes()))],
                  funding=dict(mode='RECORDED',path='funding.parquet',start=z(START),end=z(START+timedelta(hours=count)),
                               rows=len(funding),interval_seconds=28800,logical_hash=hashed(encoded(funding_material)),
                               byte_hash=hashed((root/'funding.parquet').read_bytes()),rate_unit='FRACTION_PER_EVENT',
                               notional_basis='ENTRY_FILL_PRICE_X_BASE_QUANTITY'),created_at=z(START+timedelta(hours=count)))
    save_manifest(root,manifest)
    return manifest

def save_manifest(root,manifest): (Path(root)/'dataset.json').write_bytes(encoded(manifest))

def split_policy():
    return dict(schema_version='r7-split-policy-v0.2',policy_id='FIXTURE_SPLIT',generation=1,namespace='FIXTURE',
                training=dict(start=z(START),end=z(START+timedelta(hours=4))),
                development=dict(start=z(START+timedelta(hours=4)),end=z(START+timedelta(hours=8))),
                sealed_oos=dict(start=z(START+timedelta(hours=8)),end=z(START+timedelta(hours=12))),
                warmup_bars=2,max_holding_seconds=3600,label_horizon_seconds=3600,
                embargo_seconds=3600,embargo_rationale='Fixture one hour boundary exclusion')
