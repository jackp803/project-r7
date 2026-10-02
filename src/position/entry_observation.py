"""E5 composes actual E4 entry observations into its canonical lifecycle graph.

No signal, acknowledgement or requested quantity is treated as an actual fill.
The existing lifecycle builders/state machine remain the transition authority.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib

from execution.gateway import ExecutionGateway
from execution.models import (
    ExecutionHealthStatus, Fill, OrderRequest, OrderResult, OrderStatus,
    PositionExposureSnapshot, Side, require_utc,
)
from .lifecycle_execution_binding import (
    build_position_lifecycle_genesis_with_execution_binding,
    build_position_lifecycle_transition_with_execution_binding,
    build_position_lifecycle_reattestation_with_execution_binding,
)
from .lifecycle_projection import validate_position_lifecycle_projection
from .state_machine import PositionEvent, PositionLifecycleState


@dataclass(frozen=True)
class EntryProjectionOutcome:
    projections: tuple


def build_entry_projection(plan, request, result, fills, position_snapshot, *,
                           observed_at: datetime, previous_projection=None):
    require_utc(observed_at, 'entry observation')
    if (not isinstance(request, OrderRequest) or not isinstance(result, OrderResult)
        or not isinstance(position_snapshot, PositionExposureSnapshot)):
        raise ValueError('Actual canonical E4 entry/order/position observations required')
    expected = ExecutionGateway().prepare_entry_order(plan, now=request.created_at)
    if (expected.safety_fingerprint() != request.safety_fingerprint()
        or expected.order_request_id != request.order_request_id
        or result.client_order_id != request.client_order_id
        or result.order_request_id != request.order_request_id
        or result.requested_quantity != request.quantity
        or result.execution_health_status != ExecutionHealthStatus.HEALTHY
        or result.order_status not in (OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED,
                                      OrderStatus.CANCELED, OrderStatus.EXPIRED)):
        raise ValueError('Entry observation does not match original E5-approved request')
    require_utc(result.observed_at, 'order observation')
    fills = tuple(fills)
    if not fills or len(fills) > 100_000: raise ValueError('Entry requires bounded actual fills')
    seen, quantity, average = set(), Decimal('0'), Decimal('0')
    for fill in fills:
        if not isinstance(fill, Fill): raise ValueError('Actual canonical E4 Fill required')
        require_utc(fill.filled_at, 'entry fill')
        if (fill.fill_id in seen or fill.quantity <= 0 or not fill.quantity.is_finite()
            or fill.price <= 0 or not fill.price.is_finite()
            or fill.filled_at < request.created_at or fill.filled_at > observed_at
            or fill.client_order_id != request.client_order_id or fill.broker_order_id != result.broker_order_id
            or fill.trade_plan_id != plan['trade_plan_id'] or fill.side != request.side or fill.symbol != request.symbol
            or any(getattr(fill, name) is not None for name in ('position_action_id', 'position_id', 'order_role'))):
            raise ValueError('Entry fill lineage, quantity or clock is inconsistent')
        seen.add(fill.fill_id)
        average = (average * quantity + fill.price * fill.quantity) / (quantity + fill.quantity)
        quantity += fill.quantity
    signed_quantity = quantity if request.side == Side.BUY else -quantity
    if (quantity != result.filled_quantity or quantity > request.quantity
        or position_snapshot.symbol != request.symbol or position_snapshot.net_quantity != signed_quantity
        or result.observed_at > observed_at or result.average_fill_price is None
        or not result.average_fill_price.is_finite() or result.average_fill_price != average):
        raise ValueError('Actual entry fills/order/net position cannot be reconciled')
    position_id = 'paperpos_' + hashlib.sha256(request.trade_plan_id.encode('utf-8')).hexdigest()
    source = dict(schema_version='contracts-v0.1', position_id=position_id, symbol=request.symbol,
        side=plan['direction'], actual_quantity=format(quantity, 'f'),
        average_entry_price=format(result.average_fill_price, 'f'),
        opened_at=min(fill.filled_at for fill in fills).isoformat().replace('+00:00', 'Z'),
        broker_state_observed_at=observed_at.isoformat().replace('+00:00', 'Z'),
        reconciliation_status='CONSISTENT', lifecycle_state='PENDING_ENTRY',
        quantity_profile_version=request.quantity_profile_version, quantity_unit=request.quantity_unit,
        quantity_asset=request.quantity_asset)
    evidence = dict(order_requests=(request,), order_results=(result,), fills=fills,
                    lifecycle_interpreted_at=observed_at)
    if previous_projection is None:
        genesis = build_position_lifecycle_genesis_with_execution_binding(source,
            lifecycle_state=PositionLifecycleState.PENDING_ENTRY, **evidence)
        opened = build_position_lifecycle_transition_with_execution_binding(source,
            genesis.lifecycle_projection, lifecycle_event=PositionEvent.ENTRY_FILL_OBSERVED, **evidence)
        return EntryProjectionOutcome((genesis, opened))
    validate_position_lifecycle_projection(previous_projection)
    if (previous_projection['position_id'] != position_id or
        previous_projection['opened_at'] != source['opened_at'] or
        quantity < Decimal(previous_projection['actual_quantity'])):
        raise ValueError('Entry partial fill changed first-fill identity or reduced exposure')
    previous_state = previous_projection['lifecycle_state']
    if previous_state not in ('OPEN_UNPROTECTED', 'OPEN_PROTECTED', 'PROFIT_PROTECTED'):
        raise ValueError('Entry refresh cannot replace a closing or unknown lifecycle')
    source['lifecycle_state'] = previous_state
    if (quantity > Decimal(previous_projection['actual_quantity'])
        and previous_state in ('OPEN_PROTECTED', 'PROFIT_PROTECTED')):
        current = build_position_lifecycle_transition_with_execution_binding(source,
            previous_projection, lifecycle_event=PositionEvent.PROTECTION_LOST, **evidence)
    else:
        current = build_position_lifecycle_reattestation_with_execution_binding(source,
            previous_projection, **evidence)
    return EntryProjectionOutcome((current,))
