"""Strict pure v0.2 readback around canonical E4 parsers; ACK never proves fills.

Algorithmic stop readback yields child identities only. Its triggered/actual-size
fields cannot stand in for a canonical fill or newer flat-position observation.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
import re

from brokers.okx_demo import parse_place_order_ack, parse_order_lookup_response, parse_fills_response
from brokers.okx_product import ProductOrderPreparation, OKXProductError
from brokers.okx_product_capability import CAPABILITY_PROFILE
from execution.models import require_utc, OrderResult, Fill


def _fail():
    raise OKXProductError('PRODUCT_PROVIDER_READBACK_BINDING_INVALID')


def _prepared(prepared):
    if (type(prepared) is not ProductOrderPreparation or prepared.capability_profile != CAPABILITY_PROFILE or
        prepared.role not in {'ENTRY', 'PROTECTION_STOP', 'POSITION_EXIT', 'EMERGENCY_EXIT'}):
        _fail()
    return prepared.materialization


def _id(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9]{1,64}', value):
        _fail()
    return value


def _decimal(value):
    if not isinstance(value, str) or len(value) > 128 or not re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value):
        _fail()
    return Decimal(value)


def _boolean(value):
    if value is True or value == 'true':
        return True
    if value is False or value == 'false':
        return False
    _fail()


def _rows(response):
    if not isinstance(response, dict) or not isinstance(response.get('code'), str) or not isinstance(response.get('data'), list):
        _fail()
    return response['data']


def _fields(row, prepared):
    if not isinstance(row, dict):
        _fail()
    body = prepared.materialization.body
    for key in ('instId', 'tdMode', 'posSide', 'side', 'ordType'):
        if row.get(key) != body[key]:
            _fail()
    if row.get('instType') != 'SWAP' or _decimal(row.get('sz')) != prepared.materialization.provider_contract_quantity:
        _fail()
    if _boolean(row.get('reduceOnly')) != body.get('reduceOnly', False):
        _fail()


def parse_product_ack(response, prepared, *, observed_at):
    materialization = _prepared(prepared)
    require_utc(observed_at, 'observed_at')
    rows = _rows(response)
    normalized = dict(code=response['code'], data=[])
    if len(rows) == 1 and isinstance(rows[0], dict):
        row = rows[0]
        key, identity = ('algoClOrdId', 'algoId') if prepared.role == 'PROTECTION_STOP' else ('clOrdId', 'ordId')
        native_id = row.get(identity)
        if response['code'] == '0' and row.get('sCode') == '0':
            _id(native_id)
        elif not isinstance(native_id, str) or not re.fullmatch('[0-9]{1,64}', native_id):
            native_id = None
        normalized['data'] = [dict(clOrdId=row.get(key), ordId=native_id, sCode=row.get('sCode'), sMsg='PROVIDER_ORDER_REJECTED')]
    result = parse_place_order_ack(normalized, materialization, observed_at=observed_at)
    if result.reject_reason:
        return replace(result, reject_reason='PROVIDER_ORDER_REJECTED' if result.order_status.value == 'REJECTED' else 'PROVIDER_ACK_RECONCILIATION_REQUIRED')
    return result


def parse_product_order(response, prepared, *, observed_at, expected_provider_id=None):
    materialization = _prepared(prepared)
    require_utc(observed_at, 'observed_at')
    if prepared.role == 'PROTECTION_STOP':
        _fail()
    rows = _rows(response)
    if response['code'] == '0' and rows:
        if len(rows) != 1:
            _fail()
        row = rows[0]
        _fields(row, prepared)
        provider_id = _id(row.get('ordId'))
        if expected_provider_id is not None and provider_id != _id(expected_provider_id):
            _fail()
        # Native zero avgPx is allowed only when no quantity has filled. The
        # canonical parser still validates state/fill coherence and overfills.
        if _decimal(row.get('accFillSz')) == 0 and row.get('avgPx') == '0':
            response = dict(response, data=[dict(row, avgPx='')])
    result = parse_order_lookup_response(response, materialization, observed_at=observed_at)
    if result.result is not None and result.result.reject_reason:
        result = replace(result, result=replace(result.result, reject_reason='PROVIDER_ORDER_RECONCILIATION_REQUIRED'))
    if result.provider_error_code is not None:
        result = replace(result, provider_error_code='PROVIDER_LOOKUP_ERROR')
    return result


def parse_product_fills(response, prepared, *, expected_provider_id):
    materialization = _prepared(prepared)
    if prepared.role == 'PROTECTION_STOP':
        _fail()  # Require a separately verified spawned child order binding.
    provider_id = _id(expected_provider_id)
    rows = _rows(response)
    selected, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or row.get('instId') != 'BTC-USDT-SWAP':
            _fail()
        if row.get('clOrdId') != materialization.provider_cl_ord_id:
            continue
        if (_id(row.get('ordId')) != provider_id or row.get('side') != materialization.provider_side or
            row.get('posSide') != 'net'):
            _fail()
        trade_id = _id(row.get('tradeId'))
        if trade_id in seen:
            _fail()
        seen.add(trade_id)
        _decimal(row.get('fillSz')); _decimal(row.get('fillPx'))
        fee = row.get('fee')
        if fee is not None and (not isinstance(fee, str) or len(fee) > 128 or
            not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', fee)):
            _fail()
        if not isinstance(row.get('feeCcy'), str) or not re.fullmatch('[A-Z0-9_]{1,32}', row['feeCcy']):
            _fail()
        selected.append(row)
    fills = parse_fills_response(dict(code=response['code'], data=selected), materialization)
    request = prepared.canonical_request
    if request.order_role != 'ENTRY':
        fills = tuple(replace(fill, position_action_id=request.position_action_id,
                              position_id=request.position_id, order_role=request.order_role) for fill in fills)
    return fills


@dataclass(frozen=True)
class ProductAlgoObservation:
    status: str
    provider_algo_id: str | None
    child_order_ids: tuple[str, ...]
    reason_code: str


@dataclass(frozen=True)
class ProductStopChildReadback:
    profile: str
    algo: ProductAlgoObservation
    child_result: OrderResult
    parent_result: OrderResult
    fills: tuple[Fill, ...]


def parse_product_stop_child(algo_response, order_response, fills_response, prepared, *, observed_at, expected_provider_id):
    """Interpret an exact spawned market child; these facts grant no effect.

    Canonical result retains the parent algo identity; fills retain their actual
    child broker identity and original internal action/position lineage. Native
    actualSz and triggered states cannot substitute for complete fill truth.
    """
    require_utc(observed_at, 'observed_at')
    algo = parse_product_algo(algo_response, prepared, expected_provider_id=expected_provider_id)
    if algo.status != 'TRIGGERED_REQUIRES_CHILD_ORDER' or len(algo.child_order_ids) != 1:
        _fail()
    rows = _rows(order_response)
    if order_response['code'] != '0' or len(rows) != 1 or not isinstance(rows[0], dict):
        _fail()
    native_client = rows[0].get('clOrdId')
    if not isinstance(native_client, str) or not re.fullmatch('[A-Za-z0-9]{0,32}', native_client):
        _fail()
    original = prepared.materialization
    body = {key: original.body[key] for key in ('instId', 'tdMode', 'posSide', 'side', 'sz', 'reduceOnly')}
    body.update(ordType='market', clOrdId=native_client)
    child_materialization = replace(original, provider_cl_ord_id=native_client, body=body)
    # Pure readback context only. It is not registered with an issuer and cannot
    # pass OKXProductTranslator.require or authorize a new request.
    child_context = replace(prepared, role='POSITION_EXIT', materialization=child_materialization)
    lookup = parse_product_order(order_response, child_context, observed_at=observed_at,
                                 expected_provider_id=algo.child_order_ids[0])
    if lookup.lookup_status != 'FOUND_CONSISTENT' or lookup.result is None:
        _fail()
    fills = parse_product_fills(fills_response, child_context, expected_provider_id=algo.child_order_ids[0])
    quantity = sum((fill.quantity for fill in fills), Decimal('0'))
    if quantity != lookup.result.filled_quantity or any(fill.filled_at > observed_at for fill in fills):
        _fail()
    if quantity and sum((fill.quantity * fill.price for fill in fills), Decimal('0')) / quantity != lookup.result.average_fill_price:
        _fail()
    return ProductStopChildReadback('okx-product-stop-child-readback-v0.2', algo, lookup.result,
                                   replace(lookup.result, broker_order_id=algo.provider_algo_id), fills)


def parse_product_algo(response, prepared, *, expected_provider_id=None):
    _prepared(prepared)
    if prepared.role != 'PROTECTION_STOP':
        _fail()
    rows = _rows(response)
    if response['code'] != '0' or not rows:
        return ProductAlgoObservation('RECONCILIATION_REQUIRED', None, (), 'ALGO_LOOKUP_NOT_ABSENCE_PROOF')
    if len(rows) != 1:
        _fail()
    row = rows[0]
    _fields(row, prepared)
    body = prepared.materialization.body
    if (row.get('algoClOrdId') != body['algoClOrdId'] or row.get('slTriggerPxType') != 'last' or
        row.get('slOrdPx') != '-1' or _decimal(row.get('slTriggerPx')) != _decimal(body['slTriggerPx'])):
        _fail()
    native_id = _id(row.get('algoId'))
    if expected_provider_id is not None and native_id != _id(expected_provider_id):
        _fail()
    children = row.get('ordIdList')
    if (not isinstance(children, list) or len(children) > 1 or any(_id(child) != child for child in children) or
        len(set(children)) != len(children) or (row.get('ordId') not in ('', None) and row['ordId'] not in children)):
        _fail()
    actual_size = _decimal(row.get('actualSz'))
    if actual_size > prepared.materialization.provider_contract_quantity:
        _fail()
    state = row.get('state')
    if state == 'live':
        if children or actual_size != 0 or row.get('failCode') not in ('', None):
            _fail()
        return ProductAlgoObservation('ACTIVE', native_id, (), 'NATIVE_EXACT_STOP_ACTIVE')
    if state == 'effective':
        if len(children) != 1 or row.get('failCode') not in ('', None):
            _fail()
        return ProductAlgoObservation('TRIGGERED_REQUIRES_CHILD_ORDER', native_id, tuple(children), 'NATIVE_STOP_TRIGGERED_NOT_FILL')
    if state == 'canceled' and not children and actual_size == 0:
        return ProductAlgoObservation('CANCELED', native_id, (), 'NATIVE_STOP_CANCELED')
    return ProductAlgoObservation('RECONCILIATION_REQUIRED', native_id, tuple(children), 'NATIVE_STOP_STATE_NOT_PROVEN')
