"""Recover actual committed close intent; no provider observation or effect.

The immutable claim clock identifies local history. The original broker clock
stays unchanged; the later local E5 interpretation clock is recorded separately.
Only an original durable request is added after claim-only process loss. No
acknowledgment, fill, flatness, funding or final closure is manufactured.
"""
from application.trading.admission import RuntimeAdmissionError
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_state import restore_product_readback
from brokers.paper_state import decode_fact,encode_fact
from execution.close import prepare_close_order
from execution.models import OrderRequest,OrderResult,Fill
from position.lifecycle_projection import _broker_fact_payload,build_position_lifecycle_transition
from position import build_position_lifecycle_execution_evidence_binding
from position.state_machine import PositionEvent
from registry.product_assessment import canonical
from storage.product_position import ProductCloseIntent


def _stage(service,operation,claimed_at,generation):
    prepared=restore_product_readback(operation.request);request=prepared.canonical_request
    if operation.run_id!=service.run_id or prepared.role not in ('POSITION_EXIT','EMERGENCY_EXIT'):
        raise RuntimeAdmissionError('ORIGINAL_OWNED_CLOSE_INTENT_REQUIRED')
    subject=service.canonical.current_execution_subject(service.identity,request.trade_plan_id)
    recovered=service.canonical.recover(trade_plan_id=request.trade_plan_id,position_id=request.position_id)
    reinterpret=(recovered.status=='REINTERPRETATION_REQUIRED' and
        recovered.reason_codes==('E5_EXECUTION_REINTERPRETATION_REQUIRED',) and recovered.current_lifecycle_execution_binding is not None)
    if (not (recovered.restart_authoritative or reinterpret) or recovered.current_position_projection is None or
        canonical_okx_close_sizing_hash(recovered.current_position_projection.payload)!=prepared.source_position_hash or
        canonical_okx_close_sizing_hash(subject.approved_trade_plan.payload)!=prepared.source_plan_hash):
        raise RuntimeAdmissionError('CLOSE_INTENT_ORIGINAL_CURRENT_E5_SOURCE_REQUIRED')
    source=recovered.current_position_projection.payload
    actions=[row.payload for row in recovered.position_actions if row.canonical_id==request.position_action_id]
    if (len(actions)!=1 or canonical_okx_close_sizing_hash(actions[0])!=prepared.source_action_hash or
        prepare_close_order(actions[0],subject.approved_trade_plan.payload,source,now=request.created_at)!=request):
        raise RuntimeAdmissionError('CLOSE_INTENT_ORIGINAL_E5_ACTION_REQUIRED')
    requests=tuple(decode_fact(OrderRequest,row.payload) for row in recovered.order_requests)
    entries=[row for row in requests if row.order_role in (None,'ENTRY')]
    if len(entries)!=1:raise RuntimeAdmissionError('CLOSE_INTENT_ORIGINAL_ENTRY_REQUIRED')
    entry=service.dispatch.operation(service.run_id,entries[0].order_request_id)
    if (entry is None or entry.recovery_disposition!='READBACK_REQUIRED' or
        restore_product_readback(entry.request).canonical_request!=entries[0]):
        raise RuntimeAdmissionError('CLOSE_INTENT_ORIGINAL_ENTRY_REQUIRED')
    same=[row for row in requests if row.order_request_id==request.order_request_id]
    if same and same!=[request]:raise RuntimeAdmissionError('CLOSE_INTENT_ORIGINAL_REQUEST_CONFLICT')
    if not same:requests=(*requests,request)
    results=tuple(decode_fact(OrderResult,row.payload) for row in recovered.order_result_observations)
    fills=tuple(decode_fact(Fill,row.payload) for row in recovered.fills)
    now=service.clock()
    projection=build_position_lifecycle_transition(dict(_broker_fact_payload(source),lifecycle_state=source['lifecycle_state']),
        source,lifecycle_event=PositionEvent.EXIT_REQUESTED,lifecycle_interpreted_at=now)
    binding=build_position_lifecycle_execution_evidence_binding(projection,order_requests=requests,order_results=results,fills=fills)
    effects=[dict(kind='ORDER_REQUEST',payload=encode_fact(request)),dict(kind='POSITION_PROJECTION',payload=projection),
        dict(kind='LIFECYCLE_EXECUTION_BINDING',payload=binding)]
    observation=ProductCloseIntent(entry.operation_id,canonical(source),canonical(actions[0]),claimed_at,now)
    service.canonical.require_current_execution_subject(subject)
    if service.canonical.recover(trade_plan_id=request.trade_plan_id,position_id=request.position_id)!=recovered:
        raise RuntimeAdmissionError('CLOSE_INTENT_CANONICAL_GRAPH_CHANGED')
    service.dispatch.observe_position(service.run_id,operation.operation_id,observation,effects,
        lease=service.lease,now=service.clock(),claim_inventory_generation=generation)


def recover_close_intents(service):
    # Drain existing bundles before calling this producer. Rescan after every
    # local commit rather than treating a partly consumed inventory as current.
    for count in range(1000):
        generation=service.dispatch.claim_inventory_generation()
        rows=service.dispatch.pending_close_intent_claims(service.run_id,limit=1)
        if not rows:return count
        operation,claimed_at=rows[0]
        _stage(service,operation,claimed_at,generation)
        service._coordinator().recover_publications()
    raise RuntimeAdmissionError('CLOSE_INTENT_PUBLICATION_BACKLOG')
