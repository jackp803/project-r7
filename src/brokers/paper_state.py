"""E4-owned JSON checkpoint codec for the existing deterministic PaperBroker.

This is simulation state, never a provider observation or execution permission.
Restore does not submit orders, replay fills, renew clocks or retain retry tokens.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import fields
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from execution.models import (
    SCHEMA_VERSION, ExecutionHealthStatus, Fill, OrderRequest, OrderResult,
    OrderStatus, Side, require_utc,
)

PROFILE = 'r7-paper-broker-state-v0.2'
MAX_STATE_BYTES = 16 * 1024 * 1024
MAX_ORDERS = 100_000
_DECIMALS = frozenset(('quantity', 'price', 'limit_price', 'stop_price', 'fee',
                      'requested_quantity', 'filled_quantity', 'average_fill_price'))
_TIMES = frozenset(('created_at', 'observed_at', 'filled_at'))
_ENUMS = {'side': Side, 'order_status': OrderStatus,
          'execution_health_status': ExecutionHealthStatus}


def canonical_state_json(value: Any) -> str:
    try:
        text = json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False)
        if len(text.encode('utf-8')) > MAX_STATE_BYTES:
            raise ValueError('Paper checkpoint exceeds bounded state size')
        return text
    except (TypeError, RecursionError) as exc:
        raise ValueError('Paper checkpoint must be bounded JSON') from exc


def _exact(value: Any, names: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != names:
        raise ValueError('Paper checkpoint has missing or unrecognized fields')
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 4096 or '\x00' in value:
        raise ValueError('Paper checkpoint text must be nonempty and bounded')
    return value


def encode_fact(value: OrderRequest | OrderResult | Fill) -> dict[str, Any]:
    if type(value) not in (OrderRequest, OrderResult, Fill):
        raise ValueError('Only canonical E4 execution facts may be serialized')
    result = {}
    for field in fields(value):
        item = getattr(value, field.name)
        if isinstance(item, Decimal): item = str(item)
        elif isinstance(item, datetime):
            require_utc(item, field.name)
            item = item.isoformat().replace('+00:00', 'Z')
        elif field.name in _ENUMS and item is not None: item = item.value
        result[field.name] = item
    # Encoding invalid in-memory facts must fail before a checkpoint is accepted.
    decode_fact(type(value), result)
    return result


def decode_fact(kind: type, value: Any) -> OrderRequest | OrderResult | Fill:
    if kind not in (OrderRequest, OrderResult, Fill):
        raise ValueError('Unsupported Paper execution fact')
    members = fields(kind)
    _exact(value, {field.name for field in members})
    result = {}
    for field in members:
        name, item = field.name, value[field.name]
        optional = 'None' in str(field.type)
        if item is None:
            if not optional: raise ValueError('Required Paper fact cannot be null')
        elif name in _DECIMALS:
            if not isinstance(item, str) or len(item) > 128:
                raise ValueError('Paper financial values require bounded decimal strings')
            try: item = Decimal(item)
            except InvalidOperation as exc: raise ValueError('Invalid Paper decimal') from exc
            if not item.is_finite(): raise ValueError('Paper financial values must be finite')
            if name != 'fee' and (item < 0 or (name != 'filled_quantity' and item == 0)):
                raise ValueError('Paper quantities/prices must be positive; filled quantity may be zero')
        elif name in _TIMES:
            if not isinstance(item, str) or not item.endswith('Z') or len(item) > 40:
                raise ValueError('Paper clocks require explicit RFC3339 UTC')
            try: item = datetime.fromisoformat(item[:-1] + '+00:00')
            except ValueError as exc: raise ValueError('Invalid Paper UTC clock') from exc
            require_utc(item, name)
        elif name in _ENUMS:
            item = _ENUMS[name](item)
        elif name == 'reduce_only':
            if type(item) is not bool: raise ValueError('reduce_only must be boolean or null')
        else: item = _text(item)
        result[name] = item
    if result['schema_version'] != SCHEMA_VERSION:
        raise ValueError('Unsupported Paper execution schema')
    return kind(**result)


def export_state(broker) -> dict[str, Any]:
    submissions = []
    for client_id, (request, acknowledgement) in sorted(broker._submissions.items()):
        order = broker._orders.get(client_id)
        submissions.append({
            'request': encode_fact(request), 'acknowledgement': encode_fact(acknowledgement),
            'order': None if order is None else {
                'result': encode_fact(order.result),
                'fills': [encode_fact(fill) for fill in order.fills],
            },
        })
    if set(broker._orders) - set(broker._submissions):
        raise ValueError('Paper order lacks original submission')
    payload = {'ambiguous_outcomes': dict(broker._ambiguous_outcomes),
               'rejected_outcomes': dict(broker._rejected_outcomes), 'submissions': submissions}
    state = {'schema_version': PROFILE, 'payload': payload,
             'payload_hash': hashlib.sha256(canonical_state_json(payload).encode('utf-8')).hexdigest()}
    restore_state(state)  # Validate the complete relational graph, not only its field shapes.
    return state


def _result_matches(result: OrderResult, request: OrderRequest) -> None:
    if (result.order_request_id != request.order_request_id or
        result.client_order_id != request.client_order_id or
        result.requested_quantity != request.quantity or
        result.filled_quantity > request.quantity or result.observed_at < request.created_at):
        raise ValueError('Paper order result does not match original request')


def _validate_order(request: OrderRequest, ack: OrderResult, order: Any):
    from .paper import _PaperOrder, _paper_order_id
    _result_matches(ack, request)
    if (ack.order_status not in (OrderStatus.OPEN, OrderStatus.REJECTED,
                                OrderStatus.RECONCILIATION_REQUIRED) or
        ack.filled_quantity != 0 or ack.average_fill_price is not None or
        ack.observed_at != request.created_at):
        raise ValueError('Original Paper submit acknowledgement is inconsistent')
    if order is None:
        if ack.order_status != OrderStatus.RECONCILIATION_REQUIRED or ack.broker_order_id is not None:
            raise ValueError('Definite Paper acknowledgement lacks authoritative order')
        return None
    _exact(order, {'result', 'fills'})
    current = decode_fact(OrderResult, order['result'])
    _result_matches(current, request)
    if not isinstance(order['fills'], list) or len(order['fills']) > MAX_ORDERS:
        raise ValueError('Paper fills must be a bounded array')
    fills = [decode_fact(Fill, item) for item in order['fills']]
    if ack.order_status == OrderStatus.REJECTED:
        if current != ack or fills or ack.broker_order_id is not None or not ack.reject_reason:
            raise ValueError('Rejected Paper order contains executable facts')
        return _PaperOrder(request, current, [])
    broker_id = _paper_order_id(request.client_order_id)
    if (current.broker_order_id != broker_id or
        current.order_status not in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.EXPIRED) or
        (ack.order_status == OrderStatus.OPEN and ack.broker_order_id != broker_id) or
        (ack.order_status == OrderStatus.RECONCILIATION_REQUIRED and ack.broker_order_id is not None)):
        raise ValueError('Paper broker order identity/status is inconsistent')
    filled, average, seen = Decimal('0'), None, set()
    for sequence, fill in enumerate(fills, 1):
        if any(getattr(fill, name) != getattr(request, name) for name in (
            'client_order_id', 'trade_plan_id', 'symbol', 'side',
            'position_action_id', 'position_id', 'order_role')) or fill.broker_order_id != broker_id:
            raise ValueError('Paper fill lineage differs from its order')
        material = f'{broker_id}|{sequence}|{fill.quantity}|{fill.price}|{fill.filled_at.isoformat()}'
        expected = 'fill_' + hashlib.sha256(material.encode('utf-8')).hexdigest()[:32]
        if fill.fill_id != expected or fill.fill_id in seen or fill.filled_at < request.created_at:
            raise ValueError('Paper fill identity or clock is inconsistent')
        seen.add(fill.fill_id)
        average = ((average or Decimal('0')) * filled + fill.price * fill.quantity) / (filled + fill.quantity)
        filled += fill.quantity
    if filled != current.filled_quantity or average != current.average_fill_price or filled > request.quantity:
        raise ValueError('Paper fill totals/average do not match current order')
    if ((current.order_status == OrderStatus.OPEN and filled != 0) or
        (current.order_status == OrderStatus.PARTIALLY_FILLED and not 0 < filled < request.quantity) or
        (current.order_status == OrderStatus.FILLED and filled != request.quantity) or
        (current.order_status in (OrderStatus.CANCELED, OrderStatus.EXPIRED) and filled == request.quantity)):
        raise ValueError('Paper order status contradicts actual fills')
    return _PaperOrder(request, current, fills)


def restore_state(state: Mapping[str, Any]):
    from .paper import PaperBroker
    _exact(state, {'schema_version', 'payload', 'payload_hash'})
    if state['schema_version'] != PROFILE:
        raise ValueError('Unsupported Paper broker checkpoint profile')
    encoded = canonical_state_json(state['payload'])
    if state['payload_hash'] != hashlib.sha256(encoded.encode('utf-8')).hexdigest():
        raise ValueError('Paper broker checkpoint hash mismatch')
    payload = _exact(state['payload'], {'ambiguous_outcomes', 'rejected_outcomes', 'submissions'})
    ambiguous, rejected = payload['ambiguous_outcomes'], payload['rejected_outcomes']
    if not isinstance(ambiguous, Mapping) or not isinstance(rejected, Mapping):
        raise ValueError('Paper scenario controls must be mappings')
    for key, value in ambiguous.items():
        _text(key)
        if type(value) is not bool: raise ValueError('Paper ambiguity control must be boolean')
    for key, value in rejected.items(): _text(key); _text(value)
    broker = PaperBroker(ambiguous_outcomes=ambiguous, rejected_outcomes=rejected)
    submissions = payload['submissions']
    if not isinstance(submissions, list) or len(submissions) > MAX_ORDERS:
        raise ValueError('Paper submissions must be a bounded array')
    for item in submissions:
        _exact(item, {'request', 'acknowledgement', 'order'})
        request = decode_fact(OrderRequest, item['request'])
        if request.client_order_id in broker._submissions:
            raise ValueError('Duplicate Paper client order identity')
        ack = decode_fact(OrderResult, item['acknowledgement'])
        order = _validate_order(request, ack, item['order'])
        broker._submissions[request.client_order_id] = (request, ack)
        if order is not None: broker._orders[request.client_order_id] = order
    return broker
