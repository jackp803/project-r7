"""Pure native algo inventory facts, without ownership or effect authority.

A paginated REST scan is not an atomic provider snapshot. Original row clocks
and byte-material hashes survive normalization; read clocks are kept separate.
External/unsupported shapes remain visible for the actual FP04/FP11 consumers.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import re

from execution.models import require_utc
from registry.product_assessment import digest


ALGO_TYPES=('conditional','oco','chase','trigger','move_order_stop',
            'iceberg','twap','smart_iceberg')
# The documented profile has eight distinct types. It never accepts a
# comma-separated union whose cursor semantics could conceal another type.
_ROW_FIELDS=frozenset({'algoId','algoClOrdId','instType','instId','ordType','state',
    'tdMode','posSide','side','sz','reduceOnly','slTriggerPx','slOrdPx',
    'slTriggerPxType','tpTriggerPx','tpOrdPx','tpTriggerPxType','actualSz',
    'actualPx','actualSide','ordId','ordIdList','cTime','uTime','failCode',
    'triggerPx','triggerPxType','orderPx','callbackRatio','callbackSpread',
    'activePx','subAlgoIdList'})


class ProductAlgoInventoryError(ValueError):
    def __init__(self,code='PRODUCT_NATIVE_ALGO_INVENTORY_INVALID'):
        self.code=code;super().__init__(code)


def _id(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9]{1,64}',value):
        raise ProductAlgoInventoryError()
    return value


def _clock(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9]{1,16}',value):
        raise ProductAlgoInventoryError()
    return datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=int(value))


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


@dataclass(frozen=True)
class ProductAlgoObject:
    provider_algo_id:str
    algo_type:str
    provider_created_at:datetime
    provider_updated_at:datetime|None
    row_json:str
    source_hash:str

    @property
    def row(self):return json.loads(self.row_json)


@dataclass(frozen=True)
class ProductAlgoInventoryObservation:
    profile:str
    objects:tuple[ProductAlgoObject,...]
    algo_types:tuple[str,...]
    coverage:str
    request_started_at:datetime
    received_at:datetime
    request_count:int
    account_hash:str
    metadata_hash:str


def parse_product_algo_page(response,*,algo_type,received_at,after=None):
    """Exact successful bounded page; errors never normalize into an empty set."""
    try:
        require_utc(received_at,'algo inventory receive')
        if algo_type not in ALGO_TYPES or (after is not None and _id(after)!=after):raise ValueError()
        if (not isinstance(response,dict) or response.get('code')!='0' or
            not isinstance(response.get('data'),list) or len(response['data'])>100):raise ValueError()
        result=[];previous=None
        for row in response['data']:
            if (not isinstance(row,dict) or row.get('instType')!='SWAP' or
                row.get('instId')!='BTC-USDT-SWAP' or row.get('ordType')!=algo_type or
                row.get('state')!='live'):raise ValueError()
            native=_id(row.get('algoId'))
            if not isinstance(row.get('algoClOrdId'),str) or not re.fullmatch('[A-Za-z0-9]{0,32}',row['algoClOrdId']):
                raise ValueError()
            if (after is not None and int(native)>=int(after) or
                previous is not None and int(native)>=int(previous)):raise ValueError()
            previous=native;created=_clock(row.get('cTime'))
            updated=None if row.get('uTime') in (None,'') else _clock(row['uTime'])
            if created>received_at or updated is not None and not created<=updated<=received_at:raise ValueError()
            # Preserve only documented mechanical fields. An independent hash
            # of the complete response row still detects other material drift.
            raw=_json(row)
            if len(raw)>65536:raise ValueError()
            normalized={key:value for key,value in row.items() if key in _ROW_FIELDS}
            if any(not isinstance(key,str) for key in row):raise ValueError()
            result.append(ProductAlgoObject(native,algo_type,created,updated,_json(normalized),digest(raw)))
        return tuple(result)
    except (ValueError,TypeError,OverflowError,AttributeError,RecursionError):
        raise ProductAlgoInventoryError() from None
