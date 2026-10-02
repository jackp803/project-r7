"""Complete finalized UTC constituent bars only; no gap stitching."""

from decimal import Decimal,localcontext
import hashlib
import json

from indicators.v02.common import REFERENCE_CONTEXT
from market_data.candle import Candle
from market_data.timeframes import SUPPORTED_TIMEFRAMES,timeframe_duration,is_timeframe_aligned

NORMALIZATION_VERSION='r7-utc-aggregation-v0.2'


def aggregate_complete(candles,target_timeframe):
    rows=tuple(candles)
    if not rows or any(not isinstance(row,Candle) for row in rows): raise ValueError('Canonical source candles required')
    if not isinstance(target_timeframe,str) or target_timeframe not in SUPPORTED_TIMEFRAMES: raise ValueError('Unsupported target timeframe')
    duration=timeframe_duration(target_timeframe)
    source_duration=timeframe_duration(rows[0].timeframe)
    if duration<=source_duration or duration%source_duration: raise ValueError('Target must be a whole larger timeframe')
    count=duration//source_duration
    if len(rows)%count or not is_timeframe_aligned(rows[0].open_time,target_timeframe): raise ValueError('Incomplete aggregation boundary')
    for i,row in enumerate(rows):
        if (not row.is_closed or row.timeframe!=rows[0].timeframe or row.symbol!=rows[0].symbol
                or not is_timeframe_aligned(row.open_time,row.timeframe) or (i and row.open_time!=rows[i-1].close_time)):
            raise ValueError('Incomplete finalized contiguous constituents')
    result=[]
    with localcontext(REFERENCE_CONTEXT):
        for start in range(0,len(rows),count):
            group=rows[start:start+count]
            material=[row.to_interchange_dict() for row in group]
            digest=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
            received=max(row.received_at for row in group) if all(row.received_at is not None for row in group) else None
            result.append(Candle('contracts-v0.1',group[0].symbol,target_timeframe,group[0].open_time,group[-1].close_time,
                                 group[0].open,max(row.high for row in group),min(row.low for row in group),group[-1].close,
                                 sum((row.volume for row in group),Decimal(0)),True,NORMALIZATION_VERSION+':'+rows[0].timeframe+'->'+target_timeframe,
                                 received_at=received,source_record_id='sha256:'+digest))
    return tuple(result)
