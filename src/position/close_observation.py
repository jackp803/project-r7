"""E5 residual projection from an executed explicit close and actual E4 facts.

This pure one-close adapter neither authorizes a provider effect nor establishes
native position identity. The read owner must verify its original issued native
observation, including explicit same-posId zero, before and after composition.
Zero remains EXIT_REQUESTED until the existing TradeResult closure owner acts.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from execution.close import prepare_close_order
from execution.models import ExecutionHealthStatus,Fill,OrderRequest,OrderResult,OrderStatus,PositionExposureSnapshot,Side,require_utc
from .entry_observation import build_product_entry_projection
from .lifecycle_projection import _broker_fact_payload,validate_position_lifecycle_projection
from .lifecycle_execution_binding import (build_position_lifecycle_transition_with_execution_binding,
    build_position_lifecycle_reattestation_with_execution_binding)
from .state_machine import PositionEvent


@dataclass(frozen=True)
class ProductCloseProjectionOutcome:
    profile: str
    projections: tuple


def _fills(value):
    if not isinstance(value,(tuple,list)) or not 1<=len(value)<=100_000 or any(type(fill) is not Fill for fill in value):
        raise ValueError('Bounded actual canonical Fill sequence required')
    for fill in value:
        if not isinstance(fill.filled_at,datetime) or not isinstance(fill.fill_id,str) or not 1<=len(fill.fill_id)<=256:
            raise ValueError('Bounded canonical fill identity and UTC clock required')
        require_utc(fill.filled_at,'close source fill')
    return tuple(sorted(value,key=lambda fill:(fill.filled_at,fill.fill_id)))


def build_product_close_projection(plan,authority,entry_request,entry_result,entry_fills,
        exit_request,exit_result,exit_fills,position_snapshot,*,source_position,previous_projection,observed_at):
    """One original E5 explicit close, cumulative actual partial/full fills.

The original positive source stays bound to the executed action. A later
EXIT_REQUESTED projection is only a monotonic history anchor. No unknown fee
or absent funding is converted to zero; neither is needed to observe exposure.
"""
    require_utc(observed_at,'close observation')
    if (type(entry_request) is not OrderRequest or type(entry_result) is not OrderResult
            or type(exit_request) is not OrderRequest or type(exit_result) is not OrderResult
            or type(position_snapshot) is not PositionExposureSnapshot):
        raise ValueError('Actual typed E4 entry, close and position facts required')
    validate_position_lifecycle_projection(source_position)
    validate_position_lifecycle_projection(previous_projection)
    entries=_fills(entry_fills);exits=_fills(exit_fills)
    # Reuse the actual entry owner validator against the original canonical
    # positive E5 source, not against a fabricated current provider observation.
    source_at=datetime.fromisoformat(source_position['broker_state_observed_at'].replace('Z','+00:00'))
    source_quantity=Decimal(source_position['actual_quantity'])
    original_exposure=PositionExposureSnapshot(source_position['symbol'],
        source_quantity if source_position['side']=='LONG' else -source_quantity)
    original=build_product_entry_projection(plan,entry_request,entry_result,entries,original_exposure,
        observed_at=source_at).projections[-1].lifecycle_projection
    if _broker_fact_payload(original)!=_broker_fact_payload(source_position):
        raise ValueError('Original entry basis must match the authoritative action source')
    expected=prepare_close_order(authority,plan,source_position,now=exit_request.created_at)
    if expected!=exit_request:
        raise ValueError('Close request must retain exact original E5 authority')
    for field in ('position_id','symbol','side','opened_at','average_entry_price',
                  'quantity_profile_version','quantity_unit','quantity_asset'):
        if previous_projection[field]!=source_position[field]:
            raise ValueError('Close refresh cannot replace original position identity or basis')
    if (previous_projection['lifecycle_revision']<source_position['lifecycle_revision']
            or previous_projection['lifecycle_state'] not in ('OPEN_UNPROTECTED','OPEN_PROTECTED','PROFIT_PROTECTED','EMERGENCY','EXIT_REQUESTED')):
        raise ValueError('Original open or closing lifecycle history required')
    require_utc(exit_result.observed_at,'close order observation')
    if (exit_result.schema_version!=exit_request.schema_version
            or exit_result.order_request_id!=exit_request.order_request_id
            or exit_result.client_order_id!=exit_request.client_order_id
            or not exit_result.broker_order_id or exit_result.requested_quantity!=exit_request.quantity
            or exit_result.execution_health_status!=ExecutionHealthStatus.HEALTHY
            or exit_result.order_status not in (OrderStatus.PARTIALLY_FILLED,OrderStatus.FILLED,OrderStatus.CANCELED,OrderStatus.EXPIRED)
            or not exit_request.created_at<=exit_result.observed_at<=observed_at):
        raise ValueError('Actual original close result and observation clock required')
    seen={fill.fill_id for fill in entries};quantity=Decimal(0);notional=Decimal(0)
    for fill in exits:
        require_utc(fill.filled_at,'close fill')
        if (fill.schema_version!=exit_request.schema_version or not fill.fill_id or fill.fill_id in seen
                or not isinstance(fill.quantity,Decimal) or not fill.quantity.is_finite() or fill.quantity<=0
                or not isinstance(fill.price,Decimal) or not fill.price.is_finite() or fill.price<=0
                or fill.trade_plan_id!=plan['trade_plan_id'] or fill.symbol!=exit_request.symbol or fill.side!=exit_request.side
                or fill.client_order_id!=exit_request.client_order_id or fill.broker_order_id!=exit_result.broker_order_id
                or fill.position_id!=exit_request.position_id or fill.position_action_id!=exit_request.position_action_id
                or fill.order_role!=exit_request.order_role
                or not max(exit_request.created_at,entries[-1].filled_at)<=fill.filled_at<=exit_result.observed_at):
            raise ValueError('Close fill lineage, quantity or observation clock is inconsistent')
        seen.add(fill.fill_id);quantity+=fill.quantity;notional+=fill.quantity*fill.price
    if (quantity!=exit_result.filled_quantity or quantity>exit_request.quantity
            or not isinstance(exit_result.average_fill_price,Decimal) or not exit_result.average_fill_price.is_finite()
            or exit_result.average_fill_price!=notional/quantity
            or exit_result.order_status==OrderStatus.FILLED and quantity!=exit_request.quantity
            or exit_result.order_status==OrderStatus.PARTIALLY_FILLED and quantity>=exit_request.quantity):
        raise ValueError('Close actual fills must reconcile with the exact cumulative order result')
    residual=source_quantity-quantity
    expected_net=residual if entry_request.side==Side.BUY else -residual
    if (residual<0 or residual>Decimal(previous_projection['actual_quantity'])
            or position_snapshot.symbol!=entry_request.symbol or not isinstance(position_snapshot.net_quantity,Decimal)
            or not position_snapshot.net_quantity.is_finite() or position_snapshot.net_quantity!=expected_net):
        raise ValueError('Actual entry/exit fills and current signed position do not reconcile')
    source=dict(_broker_fact_payload(source_position),actual_quantity=format(residual,'f'),
        broker_state_observed_at=observed_at.isoformat().replace('+00:00','Z'),
        lifecycle_state=previous_projection['lifecycle_state'])
    evidence=dict(lifecycle_interpreted_at=observed_at,order_requests=(entry_request,exit_request),
        order_results=(entry_result,exit_result),fills=(*entries,*exits))
    if previous_projection['lifecycle_state']=='EXIT_REQUESTED':
        projection=build_position_lifecycle_reattestation_with_execution_binding(source,previous_projection,**evidence)
    else:
        projection=build_position_lifecycle_transition_with_execution_binding(source,previous_projection,
            lifecycle_event=PositionEvent.EXIT_REQUESTED,**evidence)
    return ProductCloseProjectionOutcome('product-close-observation-v0.2',(projection,))
