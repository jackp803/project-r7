"""E6-local exact facts/replay checks; all financial math remains in E5."""
from dataclasses import asdict,fields
from datetime import datetime
from decimal import Decimal
import json

from position.trade_result import build_trade_result
from position.lifecycle_projection import build_position_lifecycle_closed_transition
from position.lifecycle_execution_binding import build_position_lifecycle_execution_evidence_binding
from storage._runtime_validation import canonical_payload,validate_raw_position
from storage.runtime_models import PaperRuntimeRecovery


PROFILE='fixture-original-trade-finalization-v0.2'
KINDS=('POSITION_PROJECTION','LIFECYCLE_EXECUTION_BINDING','TRADE_RESULT')
STATES=(('REINTERPRETATION_REQUIRED',frozenset({'E5_EXECUTION_REINTERPRETATION_REQUIRED'})),
 ('INCOMPLETE',frozenset({'CLOSED_POSITION_TRADE_RESULT_MISSING','LIFECYCLE_EXECUTION_BINDING_MISSING'})),
 ('INCOMPLETE',frozenset({'CLOSED_POSITION_TRADE_RESULT_MISSING'})),('READY',frozenset()))


def fail(code):
    from storage.product_dispatch import ProductDispatchError
    raise ProductDispatchError(code)


def payload(stored):
    if type(stored) is not dict or set(stored)!={'object_kind','canonical_id','payload_json','payload_hash'}:
        fail('FINALIZATION_EXACT_STORED_FACT_REQUIRED')
    value=json.loads(stored['payload_json']);_,raw,hashed=canonical_payload(value)
    if raw!=stored['payload_json'] or hashed!=stored['payload_hash']:fail('FINALIZATION_STORED_FACT_HASH_MISMATCH')
    return value


def recover_snapshot(canonical,source):
    connection=canonical._store._connection
    if connection.in_transaction:fail('FINALIZATION_IDLE_CANONICAL_READER_REQUIRED')
    connection.execute('BEGIN')
    try:return json.loads(json.dumps(asdict(canonical.recover(trade_plan_id=source['trade_plan_id'],position_id=source['position_id']))))
    finally:connection.rollback()


def build_effects(source):
    """Recompute the exact saved three effects with unchanged E5 consumers."""
    baseline=source['baseline']
    if (source.get('profile')!=PROFILE or type(baseline) is not dict or
            set(baseline)!={field.name for field in fields(PaperRuntimeRecovery)} or
            (baseline['status'],frozenset(baseline['reason_codes']))!=STATES[0] or baseline['trade_result'] is not None):
        fail('FINALIZATION_PRECISE_ORIGINAL_REINTERPRETATION_REQUIRED')
    plan=payload(baseline['approved_trade_plan']);previous=payload(baseline['current_position_projection'])
    requests={row['canonical_id']:payload(row) for row in baseline['order_requests']}
    expected={source['entry_operation_id'],source['stop_operation_id'],source['close_operation_id']}
    current={payload(row)['order_request_id']:payload(row) for row in baseline['current_order_results']}
    if len(expected)!=3 or set(requests)!=expected or set(current)!=expected:
        fail('FINALIZATION_EXACT_ORIGINAL_THREE_REQUESTS_REQUIRED')
    entry,stop,exit=(requests[source[key]] for key in ('entry_operation_id','stop_operation_id','close_operation_id'))
    # Shared entry requests deliberately retain the legacy null role. The E4
    # preparation role ENTRY is separate; E5's entry validator requires null.
    if (entry['order_role'] is not None or stop['order_role']!='PROTECTION_STOP' or
            exit['order_role'] not in ('POSITION_EXIT','EMERGENCY_EXIT') or
            current[source['entry_operation_id']]['order_status']!='FILLED' or
            current[source['close_operation_id']]['order_status']!='FILLED' or
            current[source['stop_operation_id']]['order_status']!='CANCELED' or
            Decimal(current[source['stop_operation_id']]['filled_quantity'])!=0 or
            previous['lifecycle_state']!='EXIT_REQUESTED' or Decimal(previous['actual_quantity'])!=0 or
            len(baseline['funding_evidence'])!=1):
        fail('FINALIZATION_SETTLED_FULL_ENTRY_SINGLE_EXIT_UNUSED_STOP_REQUIRED')
    fills=[payload(row) for row in baseline['fills']]
    if any(row['client_order_id'] not in {entry['client_order_id'],exit['client_order_id']} for row in fills):
        fail('FINALIZATION_NO_STOP_OR_FOREIGN_FILLS_REQUIRED')
    actions={row['canonical_id']:payload(row) for row in baseline['position_actions']}
    action=actions.get(exit['position_action_id'])
    if action is None:fail('FINALIZATION_ORIGINAL_EXIT_ACTION_REQUIRED')
    raw=source['raw_flat'];validate_raw_position(raw)
    if (source['trade_plan_id']!=plan['trade_plan_id'] or source['position_id']!=previous['position_id'] or
            raw['position_id']!=previous['position_id'] or raw['broker_state_observed_at']!=previous['broker_state_observed_at']):
        fail('FINALIZATION_ORIGINAL_FIRST_FLAT_REQUIRED')
    outcome=build_trade_result(plan,current_lifecycle_state='EXIT_REQUESTED',exit_authority=action,
        entry_order_requests=[entry],entry_fills=[row for row in fills if row['client_order_id']==entry['client_order_id']],
        exit_order_request=exit,exit_fills=[row for row in fills if row['client_order_id']==exit['client_order_id']],
        final_position=raw,funding_evidence=payload(baseline['funding_evidence'][0]))
    closed=build_position_lifecycle_closed_transition(raw,previous,trade_result_outcome=outcome,
        lifecycle_interpreted_at=datetime.fromisoformat(source['interpreted_at'].replace('Z','+00:00')))
    binding=build_position_lifecycle_execution_evidence_binding(closed,order_requests=list(requests.values()),
        order_results=[payload(row) for row in baseline['order_result_observations']],fills=fills)
    return [dict(kind=kind,payload=value) for kind,value in zip(KINDS,(closed,binding,outcome.trade_result))]


def _stored(kind,key,value):
    _,raw,hashed=canonical_payload(value)
    return dict(object_kind=kind,canonical_id=value[key],payload_json=raw,payload_hash=hashed)


def require_prefix(source,effects,current):
    """Recognize actual durable prefixes; normalize only for comparison."""
    baseline=source['baseline']
    owned=[_stored('POSITION_LIFECYCLE_PROJECTION','lifecycle_projection_id',effects[0]['payload']),
        _stored('POSITION_LIFECYCLE_EXECUTION_BINDING','lifecycle_execution_binding_id',effects[1]['payload']),
        _stored('TRADE_RESULT','trade_result_id',effects[2]['payload'])]
    found=[]
    for rows,item in ((current['lifecycle_history'],owned[0]),(current['lifecycle_execution_bindings'],owned[1]),
                      ([] if current['trade_result'] is None else [current['trade_result']],owned[2])):
        matches=[row for row in rows if row['canonical_id']==item['canonical_id']]
        if matches and matches!=[item]:fail('FINALIZATION_OWNED_EFFECT_CONFLICT')
        found.append(bool(matches))
    prefixes=([False,False,False],[True,False,False],[True,True,False],[True,True,True])
    if found not in prefixes:fail('FINALIZATION_ORDERED_DURABLE_PREFIX_REQUIRED')
    prefix=prefixes.index(found)
    if (current['status'],frozenset(current['reason_codes']))!=STATES[prefix]:
        fail('FINALIZATION_ACTUAL_RECOVERY_STATE_NOT_EXPECTED_PREFIX')
    projection=baseline['current_position_projection'] if not prefix else owned[0]
    binding=baseline['current_lifecycle_execution_binding'] if not prefix else (None if prefix==1 else owned[1])
    if (current['current_position_projection']!=projection or current['current_lifecycle_execution_binding']!=binding or
            current['trade_result']!=(owned[2] if prefix==3 else None)):
        fail('FINALIZATION_EXACT_CURRENT_PREFIX_POINTERS_REQUIRED')
    normalized=dict(current)
    normalized['lifecycle_history']=[x for x in current['lifecycle_history'] if x!=owned[0]]
    normalized['lifecycle_execution_bindings']=[x for x in current['lifecycle_execution_bindings'] if x!=owned[1]]
    normalized['current_position_projection']=baseline['current_position_projection']
    normalized['current_lifecycle_execution_binding']=baseline['current_lifecycle_execution_binding']
    normalized['trade_result']=None
    # Actual diagnostics were validated above; they are never rewritten to
    # manufacture operational READY or hidden from the real recovery result.
    normalized['status']=baseline['status'];normalized['reason_codes']=baseline['reason_codes']
    if normalized!=baseline:fail('FINALIZATION_UNRELATED_CANONICAL_MUTATION')
    return prefix
