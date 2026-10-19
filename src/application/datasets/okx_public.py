"""Bounded keyless BTC 4H acquisition, separate from offline qualification.

Official API V5 public-data docs checked 2026-10-19. Raw responses are retained;
SWAP vol is contracts, volCcy is base BTC. Settled realizedRate is required.
This creates research inputs only; it never selects financial review policies.
"""
from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from http.client import HTTPException,IncompleteRead
import json
from pathlib import Path
import time
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler

from application.cloud.safe_files import write_immutable
from application.datasets.catalog import canonical,decode,digest,z,DatasetError
from indicators.v02.common import canonical_decimal
from market_data.okx import normalize_okx_history_page
from market_data.errors import MarketDataError

HISTORY='/api/v5/market/history-candles'
FUNDING='/api/v5/public/funding-rate-history'
BASE='https://www.okx.com'
INSTRUMENT='BTC-USDT-SWAP'
STEP=timedelta(hours=4)
MAX_RESPONSE=2*1024*1024

class AcquisitionError(ValueError):
    def __init__(self,code): self.code=code;super().__init__(code)
def fail(code): raise AcquisitionError(code)
def millis(value): return str(int(value.timestamp()*1000))
def decimal(value):
    if not isinstance(value,str) or len(value)>80: fail('INVALID_PUBLIC_DECIMAL')
    try: result=Decimal(value)
    except InvalidOperation: fail('INVALID_PUBLIC_DECIMAL')
    if not result.is_finite(): fail('INVALID_PUBLIC_DECIMAL')
    return canonical_decimal(str(result))
def timestamp(value):
    if not isinstance(value,str) or not value.isascii() or not value.isdigit() or len(value)>16: fail('INVALID_PUBLIC_TIMESTAMP')
    try: return datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=int(value))
    except (ValueError,OverflowError): fail('INVALID_PUBLIC_TIMESTAMP')
def save(root,relative,value): write_immutable(root,relative,canonical(value).encode('utf-8'))

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

class PublicTransport:
    """Fixed GET allowlist; each attempted request has a durable pre-I/O receipt.

    No environment proxy, authorization headers, credentials, arbitrary URL,
    automatic retries or redirects. Tests may inject an offline opener.
    """
    def __init__(self,root,*,opener=None,minimum_interval=.25):
        self.root=Path(root);self.opener=opener or build_opener(ProxyHandler({}),_NoRedirect()).open
        self.minimum_interval=minimum_interval;self.attempts=0;self.responses=0
        self.started=time.monotonic();self.previous=None

    def _parameters(self,path,params):
        required={'instId','after','limit'}|({'bar'} if path==HISTORY else set())
        if path not in (HISTORY,FUNDING) or not isinstance(params,dict) or set(params)!=required:
            raise ValueError('Fixed public read-only parameters required')
        if params['instId']!=INSTRUMENT or params['limit']!='100' or (path==HISTORY and params['bar']!='4H'):
            raise ValueError('Only selected BTC 4H public data is supported')
        timestamp(params['after'])

    request_budget=64
    deadline_seconds=300

    def get(self,path,params):
        self._parameters(path,params)
        if self.attempts>=self.request_budget or time.monotonic()-self.started>=self.deadline_seconds: fail('PUBLIC_REQUEST_BUDGET_EXHAUSTED')
        if self.previous is not None:
            time.sleep(max(0,self.minimum_interval-(time.monotonic()-self.previous)))
        sequence=f'requests/{self.attempts+1:03d}'
        url=BASE+path+'?'+urlencode(sorted(params.items()))
        save(self.root,sequence+'-attempt.json',dict(method='GET',url=url,attempt=self.attempts+1,
             prepared_at=z(datetime.now(timezone.utc)),dispatch_state='PREPARED_BEFORE_IO',authentication='NONE',mutation=False))
        self.previous=time.monotonic();status=None;raw=None;chunks=[];size=0
        try:
            request=Request(url,headers={'Accept':'application/json','User-Agent':'R7-Public-ReadOnly/0.2'},method='GET')
            self.attempts+=1
            try: response=self.opener(request,timeout=10)
            except HTTPError as error: response=error
            with response:
                self.responses+=1;status=response.status
                if response.geturl()!=url: fail('PUBLIC_REDIRECT_FORBIDDEN')
                deadline=time.monotonic()+15
                while True:
                    if time.monotonic()>deadline: fail('PUBLIC_RESPONSE_DEADLINE')
                    # read1 bounds each blocking operation to one socket read.
                    part=getattr(response,'read1',response.read)(min(65536,MAX_RESPONSE+1-size))
                    if not part: break
                    chunks.append(part);size+=len(part)
                    if size>MAX_RESPONSE: fail('PUBLIC_RESPONSE_TOO_LARGE')
                raw=b''.join(chunks)
            write_immutable(self.root,sequence+'-response.bin',raw)
            save(self.root,sequence+'-result.json',dict(http_status=status,received_at=z(datetime.now(timezone.utc)),
                 response_hash=digest(raw),response_bytes=len(raw)))
            if status!=200: fail('PUBLIC_HTTP_REJECTED')
            payload=decode(raw)
            if not isinstance(payload,dict) or payload.get('code')!='0' or not isinstance(payload.get('data'),list):
                fail('PUBLIC_PROVIDER_REJECTED')
            return payload
        except (OSError,URLError,TimeoutError,HTTPException) as error:
            if isinstance(error,IncompleteRead) and isinstance(error.partial,bytes):
                chunks.append(error.partial[:max(0,MAX_RESPONSE-size)])
            prefix=b''.join(chunks)[:MAX_RESPONSE]
            if prefix: write_immutable(self.root,sequence+'-partial-response.bin',prefix)
            save(self.root,sequence+'-failure.json',dict(reason_code='PUBLIC_TRANSPORT_UNAVAILABLE',http_status=status,
                 response_complete=False,retained_prefix_bytes=len(prefix),retained_prefix_hash=digest(prefix)))
            fail('PUBLIC_TRANSPORT_UNAVAILABLE')

def _candles(transport,start,end):
    selected={};cursor=end
    while True:
        payload=transport.get(HISTORY,dict(instId=INSTRUMENT,after=millis(cursor),limit='100',bar='4H'))
        raw=payload['data']
        if not raw: break
        if any(not isinstance(row,list) or len(row)!=9 for row in raw): fail('DOCUMENTED_BASE_VOLUME_SHAPE_REQUIRED')
        candles=normalize_okx_history_page(payload,symbol='BTC_USDT_PERP',timeframe='4h')
        by_time={timestamp(row[0]):row for row in raw}
        for candle in candles:
            at=candle.open_time
            if not start<=at<end: continue
            if at in selected: fail('DUPLICATE_CANDLE')
            if not candle.is_closed: fail('UNFINALIZED_CANDLE')
            volume=decimal(by_time[at][6])
            if Decimal(volume)<0: fail('INVALID_BASE_VOLUME')
            selected[at]=dict(schema_version=candle.schema_version,symbol=candle.symbol,timeframe=candle.timeframe,
                open_time=at,close_time=candle.close_time,**{key:decimal(str(getattr(candle,key))) for key in ('open','high','low','close')},
                volume=volume,is_closed=True,source='OKX_PUBLIC_HISTORY_CANDLES_BASE_VOLUME',received_at=None,
                source_record_id=INSTRUMENT+':4H:'+millis(at))
        lower=min(by_time)
        if lower>=cursor: fail('CANDLE_PAGINATION_NO_PROGRESS')
        if lower<=start: break
        cursor=lower
    expected=[start+i*STEP for i in range((end-start)//STEP)]
    if sorted(selected)!=expected: fail('CANDLE_COVERAGE_GAP')
    return [selected[at] for at in expected]

def _funding(transport,start,end):
    selected={};cursor=end
    while True:
        raw=transport.get(FUNDING,dict(instId=INSTRUMENT,after=millis(cursor),limit='100'))['data']
        if not raw: break
        times=[]
        for row in raw:
            if not isinstance(row,dict) or row.get('instId')!=INSTRUMENT: fail('FUNDING_INSTRUMENT_MISMATCH')
            at=timestamp(row.get('fundingTime'));times.append(at)
            if not start<=at<end: continue
            if at in selected: fail('DUPLICATE_FUNDING')
            if not row.get('realizedRate'): fail('SETTLED_FUNDING_RATE_REQUIRED')
            rate=decimal(row['realizedRate'])
            if abs(Decimal(rate))>=1: fail('INVALID_SETTLED_FUNDING_RATE')
            selected[at]=dict(event_at=at,rate=rate,source='OKX_PUBLIC_REALIZED_FUNDING_RATE')
        if len(set(times))!=len(times) or not (times==sorted(times) or times==sorted(times,reverse=True)):
            fail('INVALID_FUNDING_PAGE_ORDER')
        lower=min(times)
        if lower>=cursor: fail('FUNDING_PAGINATION_NO_PROGRESS')
        if lower<=start: break
        cursor=lower
    # Existing dataset profile is a fixed interval. Never impute missing rates
    # or silently reinterpret an exchange change in BTC's settlement interval.
    interval=timedelta(hours=8)
    expected=[start+i*interval for i in range((end-start+interval-timedelta(microseconds=1))//interval)]
    if sorted(selected)!=expected: fail('FUNDING_COVERAGE_OR_INTERVAL_UNSUPPORTED')
    return [selected[at] for at in expected]

def _logical(rows):
    return digest(canonical([{key:z(value) if isinstance(value,datetime) else value for key,value in row.items()}
                              for row in rows]).encode('utf-8'))

def _write_parquet(root,name,rows,schema):
    import pyarrow as pa
    import pyarrow.parquet as pq
    output=pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(rows,schema=schema),output,compression='zstd',row_group_size=64)
    raw=output.getvalue().to_pybytes();write_immutable(root,name,raw)
    return digest(raw)

def acquire_okx_public_dataset(destination,*,start,end,_opener=None,_minimum_interval=.25):
    """Fresh bounded local dataset with retained success OR rejection accounting."""
    from application.platform.supervision import _local_path
    root=Path(destination).absolute();_local_path(root)
    if root.exists(): raise ValueError('Fresh isolated public dataset directory required')
    for value in (start,end):
        if not isinstance(value,datetime) or value.utcoffset()!=timedelta(0) or value.minute or value.second or value.microsecond:
            raise ValueError('Aligned UTC public history range required')
    if start.hour%8 or end.hour%4 or not timedelta(hours=8)<=end-start<=timedelta(days=89) or end>datetime.now(timezone.utc):
        raise ValueError('Bounded completed UTC BTC history range required')
    root.mkdir(parents=True,exist_ok=False)
    transport=PublicTransport(root,opener=_opener,minimum_interval=_minimum_interval)
    result=dict(schema_version='r7-public-acquisition-v0.2',status='ACQUISITION_REJECTED',
        start=z(start),end=z(end),symbol='BTC_USDT_PERP',timeframe='4h',provider='OKX_PUBLIC',
        credentials='NONE',provider_mutation=0,private_requests=0,promotion='NOT_ASSESSED',
        volume_mapping='OKX_VOL_CCY_BASE_BTC;RAW_VOL_CONTRACTS_RETAINED',funding_mapping='REALIZED_RATE_ONLY',
        offline_qualification='NOT_RUN',reason_code=None)
    try:
        rows=_candles(transport,start,end);funding=_funding(transport,start,end)
        import pyarrow as pa
        from application.datasets.resolver import candle_schema
        candle_hash=_write_parquet(root,'candles.parquet',rows,candle_schema())
        schema=pa.schema([pa.field('event_at',pa.timestamp('ms',tz='UTC'),False),pa.field('rate',pa.string(),False),pa.field('source',pa.string(),False)])
        funding_hash=_write_parquet(root,'funding.parquet',funding,schema)
        created=z(datetime.now(timezone.utc))
        manifest=dict(schema_version='r7-dataset-v0.2',dataset_id='okx-public-btc-4h',dataset_version=digest(canonical([z(start),z(end),_logical(rows),_logical(funding)]).encode())[7:31],
            namespace='LOCAL_RESEARCH',symbol='BTC_USDT_PERP',source_instrument=INSTRUMENT,normalization_version='r7-canonical-e1-v0.2',alignment='UTC',
            availability_model='historical_close_assumption',information_cutoff=created,created_at=created,
            units=dict(price='USDT_PER_BASE',volume='BASE',quantity='BASE',settlement='USDT',instrument_type='LINEAR_PERPETUAL'),
            candles=[dict(path='candles.parquet',timeframe='4h',start=z(start),end=z(end),rows=len(rows),finalized_rows=len(rows),missing_ranges=[],duplicate_ranges=[],
                          logical_hash=_logical(rows),byte_hash=candle_hash)],
            funding=dict(mode='RECORDED',path='funding.parquet',start=z(start),end=z(end),rows=len(funding),interval_seconds=28800,
                logical_hash=_logical(funding),byte_hash=funding_hash,rate_unit='FRACTION_PER_EVENT',notional_basis='ENTRY_FILL_PRICE_X_BASE_QUANTITY'))
        save(root,'dataset.json',manifest)
        result.update(status='DATASET_ACQUIRED',dataset_ref='dataset.json',manifest_hash=digest(canonical(manifest).encode()),
                      candle_rows=len(rows),funding_rows=len(funding),missing_ranges=[],duplicate_ranges=[])
    except AcquisitionError as error: result['reason_code']=error.code
    except (DatasetError,MarketDataError,ValueError,TypeError,KeyError): result['reason_code']='PUBLIC_RESPONSE_OR_NORMALIZATION_INVALID'
    result.update(provider_requests=transport.attempts,provider_responses=transport.responses)
    save(root,'acquisition.json',result)
    return result
