"""Bounded exact canceled-stop facts; no live inventory or effect authority."""
from dataclasses import dataclass
from datetime import datetime

from brokers.okx_product_readback import parse_product_algo
from brokers.okx_product_inventory import _clock,_json,_ROW_FIELDS
from execution.models import require_utc
from registry.product_assessment import digest


class ProductTerminalStopError(ValueError):
    def __init__(self):super().__init__('PRODUCT_EXACT_TERMINAL_STOP_NOT_PROVEN')


@dataclass(frozen=True)
class ProductTerminalStopObservation:
    status:str
    provider_algo_id:str
    provider_created_at:datetime
    provider_updated_at:datetime
    received_at:datetime
    row_json:str
    source_hash:str


def parse_product_terminal_stop(response,prepared,*,received_at,expected_provider_id):
    """CANCELED plus exact native binding, no child/fill, and original clocks.

    Successful cancel ACK, empty/error lookup, and a triggered child cannot
    substitute for this target. The separate inventory parser stays live-only.
    """
    try:
        require_utc(received_at,'terminal stop receive')
        if not isinstance(expected_provider_id,str) or not expected_provider_id:raise ValueError()
        observation=parse_product_algo(response,prepared,expected_provider_id=expected_provider_id)
        if observation.status!='CANCELED' or observation.child_order_ids:raise ValueError()
        row=response['data'][0]
        if row.get('failCode') not in ('',None) or any(not isinstance(key,str) for key in row):raise ValueError()
        raw=_json(row)
        if len(raw)>65536:raise ValueError()
        created=_clock(row.get('cTime'));updated=_clock(row.get('uTime'))
        if not created<=updated<=received_at:raise ValueError()
        normalized={key:value for key,value in row.items() if key in _ROW_FIELDS}
        return ProductTerminalStopObservation('CANCELED',observation.provider_algo_id,created,updated,
            received_at,_json(normalized),digest(raw))
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,AttributeError,RecursionError):
        raise ProductTerminalStopError() from None
