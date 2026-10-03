"""Pure bounded native position readback; this data grants no effect authority.

The native last-update clock and actual request/receive clocks have different
meanings. An unchanged position can be read now; cached data cannot renew those
clocks. Empty/error responses never prove flatness, including after a close ACK.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import re

from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_sizing import validate_okx_submit_metadata
from execution.models import PositionExposureSnapshot,require_utc


class ProductPositionObservationError(ValueError):
    def __init__(self):super().__init__('PRODUCT_NATIVE_POSITION_OBSERVATION_INVALID')


def _id(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9]{1,64}',value):raise ProductPositionObservationError()
    return value


def _number(value):
    if not isinstance(value,str) or len(value)>128 or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?',value):
        raise ProductPositionObservationError()
    return Decimal(value)


@dataclass(frozen=True)
class ProductPositionObservation:
    profile:str
    provider_position_id:str
    provider_contract_quantity:Decimal
    canonical_net_quantity:Decimal
    average_entry_price:Decimal|None
    provider_updated_at:datetime
    request_started_at:datetime
    received_at:datetime
    metadata_hash:str

    @property
    def exposure(self):return PositionExposureSnapshot('BTC_USDT_PERP',self.canonical_net_quantity)


def parse_product_position_response(response,*,metadata,request_started_at,received_at,
                                    expected_provider_position_id=None):
    try:
        require_utc(request_started_at,'position request start');require_utc(received_at,'position receive')
        if not request_started_at<=received_at<=request_started_at+timedelta(seconds=30):raise ValueError()
        validate_okx_submit_metadata(metadata,now=received_at)
        if (not isinstance(response,dict) or response.get('code')!='0' or
            not isinstance(response.get('data'),list) or len(response['data'])!=1 or
            not isinstance(response['data'][0],dict)):raise ValueError()
        row=response['data'][0]
        if any(row.get(key)!=value for key,value in dict(instType='SWAP',instId='BTC-USDT-SWAP',
            mgnMode='isolated',posSide='net',ccy='USDT').items()):raise ValueError()
        native=_id(row.get('posId'))
        if expected_provider_position_id is not None and native!=_id(expected_provider_position_id):raise ValueError()
        quantity=_number(row.get('pos'))
        if quantity==0 and expected_provider_position_id is None:raise ValueError()
        average=None if quantity==0 and row.get('avgPx') in ('','0') else _number(row.get('avgPx'))
        if average is not None and average<=0:raise ValueError()
        stamp=row.get('uTime')
        if not isinstance(stamp,str) or not re.fullmatch('[0-9]{1,16}',stamp):raise ValueError()
        updated=datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=int(stamp))
        if updated>received_at:raise ValueError()
        return ProductPositionObservation('okx-product-position-readback-v0.2',native,quantity,
            quantity*metadata.ct_val*metadata.ct_mult,average,updated,request_started_at,received_at,
            canonical_okx_close_sizing_hash(metadata))
    except (ValueError,TypeError,AttributeError,OverflowError,KeyError):
        raise ProductPositionObservationError() from None
