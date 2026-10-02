"""E5 consumer of additive exit requests. Existing E5 actions retain authority.

No quantity/risk sizing is invented here. Initial protection/close use their
canonical owner builders. Trailing proposals are explicitly non-executable
under the existing provider protection-v0.1 contract.
"""

from dataclasses import dataclass,replace
from collections.abc import Mapping
from datetime import datetime,timedelta
from decimal import Decimal,localcontext
import hashlib

from indicators.v02.common import REFERENCE_CONTEXT,finite_decimal,canonical_decimal
from market_data.current import MarketSnapshot
from position.close import (_validate_parent_plan,_validate_position,authorize_close_position_action)
from position.protection import build_protect_position_action
from position.protection_trigger_validity import build_protection_trigger_validity_evidence
from strategy.runtime import _canonical_json,_format_utc,_parse_utc,_freeze
from strategy.v02.exits import ExitRequest,EXIT_REQUEST_PROFILE


class ExitRequestError(ValueError):
    def __init__(self,code): super().__init__(code); self.code=code


def fail(code): raise ExitRequestError(code)


def _plan_hash(plan):
    def plain(value):
        if isinstance(value,Mapping): return {key:plain(child) for key,child in value.items()}
        if isinstance(value,(list,tuple)): return [plain(child) for child in value]
        if isinstance(value,Decimal): return canonical_decimal(str(value))
        return value
    return 'sha256:'+hashlib.sha256(_canonical_json(plain(plan)).encode('utf-8')).hexdigest()


def positive(value):
    try: number=finite_decimal(str(value)) if isinstance(value,Decimal) else finite_decimal(value)
    except ValueError: fail('INVALID_EXIT_DECIMAL')
    if number<=0: fail('INVALID_EXIT_DECIMAL')
    return number


@dataclass(frozen=True)
class ExitConstraints:
    stop_level: Decimal | None
    target_level: Decimal | None
    trailing_distance: Decimal | None
    max_hold_seconds: int | None


def resolve_exit_constraints(request):
    if not isinstance(request,ExitRequest): fail('EXIT_REQUEST_REQUIRED')
    value=request.as_dict()
    if value.get('exit_request_profile_version')!=EXIT_REQUEST_PROFILE: fail('UNSUPPORTED_EXIT_REQUEST_PROFILE')
    side=value.get('direction')
    if side not in {'LONG','SHORT'}: fail('INVALID_EXIT_DIRECTION')
    reference=positive(value['reference_price'])
    policy=value['exit_policy']
    sign=Decimal(-1) if side=='LONG' else Decimal(1)
    def price(item,role,stop=None):
        if item is None: return None
        kind=item['kind']
        if kind=='fixed_price': return positive(item['value'])
        if kind=='fixed_distance': distance=positive(item['value'])
        elif kind=='atr_multiple':
            anchor=value['feature_anchors'].get(item['feature'])
            if (not anchor or anchor['semantic_version']!='r7-atr-wilder-v1'
                    or anchor['market_boundary_ref']!=value['market_boundary_ref']
                    or _parse_utc(anchor['observed_at'],'atr_observed_at')>_parse_utc(value['observed_at'],'request_observed_at')):
                fail('ATR_ANCHOR_BINDING_MISMATCH')
            distance=positive(anchor['value'])*positive(item['multiple'])
        elif kind=='reward_risk' and role=='target':
            if stop is None: fail('REWARD_RISK_STOP_REQUIRED')
            distance=abs(reference-stop)*positive(item['multiple'])
        else: fail('INVALID_EXIT_REQUEST_KIND')
        return reference+(sign if role=='stop' else -sign)*distance
    with localcontext(REFERENCE_CONTEXT):
        stop=price(policy['stop'],'stop')
        target=price(policy['target'],'target',stop)
        if stop is not None and (stop<=0 or (stop>=reference if side=='LONG' else stop<=reference)): fail('INVALID_STOP_GEOMETRY')
        if target is not None and (target<=0 or (target<=reference if side=='LONG' else target>=reference)): fail('INVALID_TARGET_GEOMETRY')
        trailing=positive(policy['trailing']['value']) if policy['trailing'] else None
    hold=policy['max_hold_seconds']
    if hold is not None and (type(hold) is not int or not 1<=hold<=31536000): fail('INVALID_MAX_HOLD')
    return ExitConstraints(stop,target,trailing,hold)

def propose_trailing_stop(side,initial_stop,previous_stop,high_water,low_water,distance):
    """Shared E5 geometry only; this proposal grants no execution authority."""
    if side not in ('LONG','SHORT'): fail('INVALID_EXIT_DIRECTION')
    initial_stop,previous_stop,high_water,low_water,distance=(positive(str(value)) for value in
        (initial_stop,previous_stop,high_water,low_water,distance))
    if low_water>high_water: fail('INVALID_MARKET_EXTREMES')
    if previous_stop<initial_stop if side=='LONG' else previous_stop>initial_stop: fail('LOSS_BOUND_WIDENED')
    with localcontext(REFERENCE_CONTEXT):
        return max(previous_stop,high_water-distance) if side=='LONG' else min(previous_stop,low_water+distance)


@dataclass(frozen=True)
class ExitAnchor:
    request_hash: str
    position_id: str
    trade_plan_id: str
    approved_plan_hash: str
    side: str
    first_fill_at: datetime
    initial_reference_price: Decimal
    initial_stop: Decimal
    target_level: Decimal | None
    hold_deadline: datetime
    high_water: Decimal
    low_water: Decimal
    proposed_stop: Decimal
    last_market_at: datetime | None=None


def anchor_exit_request(request,position,plan):
    constraints=resolve_exit_constraints(request)
    value=request.as_dict()
    facts=_validate_position(position,plan,'EXIT')
    plan_facts=_validate_parent_plan(plan)
    if facts['actual_quantity']>plan_facts['maximum_quantity']: fail('ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM')
    for field in ('strategy_id','strategy_version','symbol'):
        if value[field]!=plan[field]: fail('EXIT_SUBJECT_MISMATCH')
    if value['direction']!=position['side']: fail('EXIT_SUBJECT_MISMATCH')
    instruction=plan['protection_instruction']
    stop=positive(instruction['stop_level'])
    target=positive(instruction['target_level']) if instruction.get('target_level') is not None else None
    if constraints.stop_level is not None and constraints.stop_level!=stop: fail('APPROVED_STOP_CONSTRAINT_MISMATCH')
    if constraints.target_level is not None and constraints.target_level!=target: fail('APPROVED_TARGET_CONSTRAINT_MISMATCH')
    policy_hold=instruction['max_hold_seconds']
    if type(policy_hold) is not int or policy_hold<=0: fail('INVALID_APPROVED_HOLD')
    hold=min(policy_hold,constraints.max_hold_seconds) if constraints.max_hold_seconds is not None else policy_hold
    first=_parse_utc(position['opened_at'],'first_fill_at')
    if _parse_utc(value['observed_at'],'exit_request_observed_at')>first: fail('REQUEST_AFTER_FIRST_FILL')
    reference=positive(position['average_entry_price'])
    if stop>=reference if position['side']=='LONG' else stop<=reference: fail('INVALID_FILLED_STOP_GEOMETRY')
    return ExitAnchor(request.request_hash,position['position_id'],plan['trade_plan_id'],_plan_hash(plan),position['side'],first,
                      reference,stop,target,first+timedelta(seconds=hold),reference,reference,stop)


@dataclass(frozen=True)
class CurrentExitAuthority:
    position: dict
    parent_plan: dict
    anchor: ExitAnchor
    market_snapshot: MarketSnapshot
    market_freshness_classification: str
    now: datetime
    action_expires_at: datetime

    def __post_init__(self):
        object.__setattr__(self,'position',_freeze(dict(self.position)))
        object.__setattr__(self,'parent_plan',_freeze(dict(self.parent_plan)))
        object.__setattr__(self,'now',_parse_utc(self.now,'now'))
        object.__setattr__(self,'action_expires_at',_parse_utc(self.action_expires_at,'action_expires_at'))


@dataclass(frozen=True)
class ExitOutcome:
    status: str
    anchor: ExitAnchor
    position_action: dict | None=None
    trigger_validity_evidence: dict | None=None
    lifecycle_intent: str | None=None
    reason_codes: tuple[str,...]=()


def interpret_exit_request(request,current_e5_authority):
    if not isinstance(current_e5_authority,CurrentExitAuthority): fail('CURRENT_E5_AUTHORITY_REQUIRED')
    authority=current_e5_authority
    position,plan,anchor=authority.position,authority.parent_plan,authority.anchor
    constraints=resolve_exit_constraints(request)
    value=request.as_dict()
    if (anchor.request_hash!=request.request_hash or anchor.position_id!=position['position_id']
            or anchor.trade_plan_id!=plan['trade_plan_id'] or anchor.side!=position['side']
            or anchor.approved_plan_hash!=_plan_hash(plan)):
        fail('EXIT_AUTHORITY_BINDING_MISMATCH')
    facts=_validate_position(position,plan,'EXIT')
    plan_facts=_validate_parent_plan(plan)
    if facts['actual_quantity']>plan_facts['maximum_quantity']: fail('ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM')
    if facts['observed_at']>authority.now or authority.action_expires_at<=authority.now: fail('INVALID_ACTION_TIME')
    if positive(plan['protection_instruction']['stop_level'])!=anchor.initial_stop: fail('APPROVED_STOP_CHANGED')
    if anchor.first_fill_at>_parse_utc(position['opened_at'],'opened_at'): fail('FIRST_FILL_CLOCK_MISMATCH')
    plan_hold=plan['protection_instruction']['max_hold_seconds']
    allowed_hold=min(plan_hold,constraints.max_hold_seconds) if constraints.max_hold_seconds is not None else plan_hold
    if anchor.hold_deadline!=anchor.first_fill_at+timedelta(seconds=allowed_hold): fail('HOLD_BOUND_CHANGED')
    if authority.now>=anchor.hold_deadline:
        reason='E5_MAX_HOLD_REACHED'
        closed=authorize_close_position_action(position,plan,action='EXIT',created_at=authority.now,
                                               expires_at=authority.action_expires_at,reason_codes=(reason,))
        return ExitOutcome('AUTHORIZED',anchor,closed.position_action,lifecycle_intent=closed.event.value,reason_codes=(reason,))
    market=authority.market_snapshot
    if (not isinstance(market,MarketSnapshot) or market.symbol!=position['symbol']
            or market.health_status!='HEALTHY' or authority.market_freshness_classification!='FRESH'
            or market.observed_at>authority.now or market.received_at>authority.now or market.last_price is None):
        return ExitOutcome('BLOCKED',anchor,reason_codes=('CURRENT_MARKET_UNAVAILABLE',))
    if anchor.last_market_at is not None and market.observed_at<anchor.last_market_at:
        return ExitOutcome('BLOCKED',anchor,reason_codes=('MARKET_OBSERVATION_OUT_OF_ORDER',))
    price=positive(market.last_price)
    long=anchor.side=='LONG'
    if (anchor.proposed_stop<anchor.initial_stop if long else anchor.proposed_stop>anchor.initial_stop): fail('LOSS_BOUND_WIDENED')
    # Actual verified protection is not inferred from a previous proposal.
    stop_reached=price<=anchor.initial_stop if long else price>=anchor.initial_stop
    target_reached=anchor.target_level is not None and (price>=anchor.target_level if long else price<=anchor.target_level)
    reason='E5_STOP_REACHED' if stop_reached else 'E5_MAX_HOLD_REACHED' if authority.now>=anchor.hold_deadline else 'E5_TARGET_REACHED' if target_reached else None
    if reason is not None:
        closed=authorize_close_position_action(position,plan,action='EXIT',created_at=authority.now,
                                               expires_at=authority.action_expires_at,reason_codes=(reason,))
        return ExitOutcome('AUTHORIZED',anchor,closed.position_action,lifecycle_intent=closed.event.value,reason_codes=(reason,))
    if position['lifecycle_state']=='OPEN_UNPROTECTED':
        action=build_protect_position_action(position,plan,created_at=authority.now,expires_at=authority.action_expires_at)
        evidence=build_protection_trigger_validity_evidence(position,action,plan,market,
                          market_freshness_classification=authority.market_freshness_classification,evaluated_at=authority.now)
        if evidence['validity_status']!='ACTIONABLE': return ExitOutcome('BLOCKED',anchor,trigger_validity_evidence=evidence,reason_codes=tuple(evidence['reason_codes']))
        return ExitOutcome('AUTHORIZED',anchor,action,evidence)
    if constraints.trailing_distance is None: return ExitOutcome('HOLD',anchor)
    with localcontext(REFERENCE_CONTEXT):
        high=max(anchor.high_water,price)
        low=min(anchor.low_water,price)
        proposed=propose_trailing_stop(anchor.side,anchor.initial_stop,anchor.proposed_stop,high,low,constraints.trailing_distance)
    advanced=replace(anchor,high_water=high,low_water=low,proposed_stop=proposed,last_market_at=market.observed_at)
    if (proposed>=price if long else proposed<=price):
        return ExitOutcome('BLOCKED',advanced,reason_codes=('TRAILING_TRIGGER_NOT_ACTIONABLE',))
    material={'schema_version':'contracts-v0.1','position_id':position['position_id'],'action':'MODIFY_PROTECTION',
              'reason_codes':['E5_TRAILING_STOP_PROPOSED','MODIFY_PROFILE_UNAVAILABLE'],
              'risk_policy_version':plan['risk_policy_version'],'created_at':_format_utc(authority.now),
              'exit_request_profile_version':EXIT_REQUEST_PROFILE,'exit_request_hash':request.request_hash,
              'stop_level':canonical_decimal(str(proposed)),'position_observed_at':position['broker_state_observed_at'],
              'trade_plan_id':plan['trade_plan_id'],'quantity':position['actual_quantity']}
    material['position_action_id']='posact_'+hashlib.sha256(_canonical_json(material).encode('utf-8')).hexdigest()
    return ExitOutcome('NON_EXECUTABLE_PROFILE',advanced,material,reason_codes=('MODIFY_PROFILE_UNAVAILABLE',))
