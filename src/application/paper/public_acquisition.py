"""Bounded BTC public market batches; no risk, execution or lifecycle authority."""
from dataclasses import asdict,replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
import re,uuid

from application.cloud.manifest import safe_component
from application.datasets.catalog import canonical,decode
from application.datasets.okx_public import PublicTransport,HISTORY,INSTRUMENT,millis,timestamp,decimal,fail,AcquisitionError,save
from application.platform.private_files import create_private_directory
from market_data.current import normalize_okx_ticker
from market_data.errors import MarketDataError
from market_data.okx import normalize_okx_history_page
from market_data.timeframes import timeframe_duration,okx_bar,is_timeframe_aligned
from .public_market import MarketSubscription

TICKER='/api/v5/market/ticker'
SCHEMA='r7-public-market-batch-v0.2'
MAX_OUTPUT=12*1024*1024


def utc(value):
    if not isinstance(value,str) or len(value)>40 or not value.endswith('Z'):raise ValueError('UTC public fact required')
    result=datetime.fromisoformat(value[:-1]+'+00:00')
    if result.utcoffset()!=timedelta(0):raise ValueError('UTC public fact required')
    return result


def validate_subscriptions(values):
    if not isinstance(values,list) or not 1<=len(values)<=200:raise ValueError('Bounded owning subscriptions required')
    result=[];seen=set();token=None
    for value in values:
        if not isinstance(value,dict) or set(value)!=set(MarketSubscription.__dataclass_fields__):raise ValueError('Exact owning subscription required')
        safe_component(value['run_id'])
        if value['run_id'] in seen:raise ValueError('Unique owning run required')
        if type(value['runtime_token']) is not str or len(value['runtime_token'])!=36:raise ValueError('Exact runtime token required')
        seen.add(value['run_id']);parsed=uuid.UUID(value['runtime_token'])
        if (parsed.version!=4 or str(parsed)!=value['runtime_token'] or token not in (None,value['runtime_token'])
                or value['namespace']!='LOCAL_RESEARCH' or value['symbol']!='BTC_USDT_PERP'
                or type(value['e6_generation']) is not int or not 1<=value['e6_generation']<=2147483647
                or type(value['strategy_content_hash']) is not str or not re.fullmatch(r'sha256:[0-9a-f]{64}',value['strategy_content_hash'])):
            raise ValueError('Exact ordinary public owning subject required')
        token=value['runtime_token'];frames=[];frame_names=set()
        if not isinstance(value['frames'],(tuple,list)) or not 1<=len(value['frames'])<=4:raise ValueError('Bounded strategy frames required')
        for row in value['frames']:
            if not isinstance(row,(tuple,list)) or len(row)!=4:raise ValueError('Exact strategy frame required')
            frame,needed,cap,last=row;timeframe_duration(frame)
            if frame in frame_names or type(needed) is not int or type(cap) is not int or not 1<=needed<=cap<=4000:
                raise ValueError('Bounded unique strategy history required')
            if last is not None and not is_timeframe_aligned(utc(last),frame):raise ValueError('Aligned durable candle boundary required')
            frames.append(tuple(row));frame_names.add(frame)
        if value['last_observed_at'] is not None:utc(value['last_observed_at'])
        result.append(MarketSubscription(**dict(value,frames=tuple(frames))))
    return tuple(result)


class PaperPublicTransport(PublicTransport):
    request_budget=165
    deadline_seconds=120
    def _parameters(self,path,params):
        if path==TICKER and params==dict(instId=INSTRUMENT):return
        if (path!=HISTORY or not isinstance(params,dict) or set(params)!={'instId','after','limit','bar'}
                or params['instId']!=INSTRUMENT or params['limit']!='100'
                or params['bar'] not in ('1m','15m','1H','4H')):raise ValueError('Fixed BTC public market GET required')
        timestamp(params['after'])


def _floor(now,frame):
    epoch=datetime(1970,1,1,tzinfo=timezone.utc);step=timeframe_duration(frame)
    return epoch+((now-epoch)//step)*step


def _history(transport,frame,start,end,clock):
    cursor=end;selected={};step=timeframe_duration(frame)
    while cursor>start:
        payload=transport.get(HISTORY,dict(instId=INSTRUMENT,after=millis(cursor),limit='100',bar=okx_bar(frame)))
        received=clock();raw=payload['data']
        if not raw:break
        if any(not isinstance(row,list) or len(row)!=9 for row in raw):fail('DOCUMENTED_BASE_VOLUME_SHAPE_REQUIRED')
        rows=normalize_okx_history_page(payload,symbol='BTC_USDT_PERP',timeframe=frame)
        originals={timestamp(row[0]):row for row in raw}
        for candle in rows:
            if not start<=candle.open_time<end:continue
            if candle.open_time in selected:fail('DUPLICATE_CANDLE')
            if not candle.is_closed or candle.close_time>received:fail('UNFINALIZED_CANDLE')
            volume=Decimal(decimal(originals[candle.open_time][6]))
            if volume<0:fail('INVALID_BASE_VOLUME')
            selected[candle.open_time]=replace(candle,volume=volume,received_at=received,
                source='OKX_PUBLIC_HISTORY_CANDLES_BASE_VOLUME',source_record_id=INSTRUMENT+':'+okx_bar(frame)+':'+millis(candle.open_time))
        lower=min(originals)
        if lower>=cursor:fail('CANDLE_PAGINATION_NO_PROGRESS')
        cursor=lower
    expected=[start+i*step for i in range((end-start)//step)]
    if sorted(selected)!=expected:fail('CANDLE_COVERAGE_GAP')
    return [selected[at].to_interchange_dict() for at in expected]


def acquire_batch(root,subscriptions,*,_opener=None,_clock=lambda:datetime.now(timezone.utc),_minimum_interval=.25):
    """Private pure acquisition component; CLI admission precedes this function.

    Every successful/rejected attempt has its actual request counters and raw
    receipts. An interrupted process has incomplete accounting, never fake zero.
    """
    subscriptions=validate_subscriptions([asdict(value) for value in subscriptions])
    root=Path(root);create_private_directory(root)
    transport=PaperPublicTransport(root,opener=_opener,minimum_interval=_minimum_interval)
    result=dict(schema_version=SCHEMA,status='PUBLIC_MARKET_REJECTED',subscriptions=[asdict(row) for row in subscriptions])
    try:
        now=_clock();ranges={};candles={}
        for row in subscriptions:
            for frame,needed,cap,last in row.frames:
                end=_floor(now,frame);start=end-needed*timeframe_duration(frame) if last is None else max(utc(last),end-cap*timeframe_duration(frame))
                if start>end:fail('FUTURE_DURABLE_CANDLE_BOUNDARY')
                if start<end:ranges[frame]=(min(start,ranges.get(frame,(start,end))[0]),end)
        for frame,(start,end) in sorted(ranges.items()):candles[frame]=_history(transport,frame,start,end,_clock)
        payload=transport.get(TICKER,dict(instId=INSTRUMENT))
        snapshot=normalize_okx_ticker(payload,symbol='BTC_USDT_PERP',received_at=_clock())
        # A boundary crossed during warmup is retried; never present incomplete
        # history as the just-closed bar associated with a newer quote.
        if any(_floor(now,frame)!=_floor(snapshot.observed_at,frame) for row in subscriptions for frame,*_ in row.frames):fail('CANDLE_BOUNDARY_CHANGED')
        result.update(status='PUBLIC_MARKET_ACQUIRED',snapshot=snapshot.to_interchange_dict(),candles=candles)
    except AcquisitionError as error:result['reason_code']=error.code
    except MarketDataError:result['reason_code']='PUBLIC_MARKET_DATA_REJECTED'
    result.update(provider_requests=transport.attempts,provider_responses=transport.responses,
        request_accounting='COMPLETE',credentials='NONE',provider_mutation=0)
    result=decode(canonical(result).encode('utf-8'))
    save(root,'acquisition.json',result)
    return result


def event_for(current,result,*,now):
    """Owner thread validates immutable child facts and both generation fences."""
    from .engine import _market,_candle
    from .service import PaperMarketEvent
    required={'schema_version','status','subscriptions','snapshot','candles','provider_requests','provider_responses',
              'request_accounting','credentials','provider_mutation'}
    if (not isinstance(result,dict) or set(result)!=required or result['schema_version']!=SCHEMA
            or result['status']!='PUBLIC_MARKET_ACQUIRED' or result['request_accounting']!='COMPLETE'
            or result['credentials']!='NONE' or type(result['provider_mutation']) is not int or result['provider_mutation']!=0
            or type(result['provider_requests']) is not int or type(result['provider_responses']) is not int
            or not 1<=result['provider_responses']<=result['provider_requests']<=165):raise ValueError('Exact actual public batch required')
    originals=validate_subscriptions(result['subscriptions'])
    original=next((row for row in originals if row.run_id==current.run_id),None)
    if original is None:return None
    if any(getattr(original,key)!=getattr(current,key) for key in
            ('namespace','runtime_token','e6_generation','strategy_content_hash','symbol')):return None
    if tuple(row[:3] for row in current.frames)!=tuple(row[:3] for row in original.frames):return None
    raw=result['snapshot']
    if (not isinstance(raw,dict) or set(raw)!={'schema_version','symbol','observed_at','received_at','health_status','source',
            'last_price','best_bid','best_ask','freshness_ms'} or raw['source']!='OKX_PUBLIC_TICKER'
            or raw['symbol']!='BTC_USDT_PERP' or raw['health_status']!='HEALTHY'
            or type(raw['freshness_ms']) is not int or not 0<=raw['freshness_ms']<=5000
            or any(not isinstance(raw[key],str) or len(raw[key])>80 for key in ('last_price','best_bid','best_ask'))):
        raise ValueError('Exact E1 public ticker required')
    observed,received=utc(raw['observed_at']),utc(raw['received_at'])
    for field in ('last_price','best_bid','best_ask'):decimal(raw[field])
    if not observed<=received<=now or (now-observed).total_seconds()>5:raise ValueError('Actual fresh available ticker required')
    if current.last_observed_at is not None and observed<=utc(current.last_observed_at):return None
    try:snapshot=_market(raw)
    except MarketDataError as error:raise ValueError('E1 public ticker rejected') from error
    rows=[];frames={row[0]:row for row in current.frames}
    all_frames={frame[0] for selected in originals for frame in selected.frames}
    if not isinstance(result['candles'],dict) or set(result['candles'])-all_frames:raise ValueError('Exact selected batch frames required')
    for frame,values in result['candles'].items():
        if not isinstance(values,list) or len(values)>4000:raise ValueError('Bounded finalized candles required')
        if frame not in frames:continue
        previous=None;last=frames[frame][3]
        for value in values:
            if (not isinstance(value,dict) or set(value)!={'schema_version','symbol','timeframe','open_time','close_time',
                    'open','high','low','close','volume','is_closed','source','received_at','source_record_id'}
                    or any(not isinstance(value[key],str) or len(value[key])>80 for key in ('open','high','low','close','volume'))
                    or value['is_closed'] is not True or value['timeframe']!=frame or value['symbol']!=current.symbol
                    or value['source']!='OKX_PUBLIC_HISTORY_CANDLES_BASE_VOLUME'):
                raise ValueError('Exact finalized E1 public candle required')
            for field in ('open','high','low','close','volume'):decimal(value[field])
            for field in ('open_time','close_time','received_at'):utc(value[field])
            if (not isinstance(value['source_record_id'],str) or value['source_record_id']!=
                    INSTRUMENT+':'+okx_bar(frame)+':'+millis(utc(value['open_time']))):raise ValueError('Exact public candle identity required')
            try:candle=_candle(value)
            except MarketDataError as error:raise ValueError('E1 public candle rejected') from error
            if (candle.received_at is None or not candle.close_time<=candle.received_at<=now
                    or not is_timeframe_aligned(candle.open_time,frame)
                    or previous is not None and candle.open_time!=previous):raise ValueError('Available contiguous finalized candles required')
            previous=candle.close_time
            if last is None or candle.close_time>utc(last):rows.append(candle)
    return PaperMarketEvent(snapshot,tuple(rows),source_kind='PUBLIC_MARKET')
