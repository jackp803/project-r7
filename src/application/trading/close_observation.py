"""Issuer-bound explicit-close exposure, kept separate from final closure.

Only the original E4 native position binding and actual E4 fills can advance
this E5 observation. Explicit flatness stays EXIT_REQUESTED; it supplies no
funding, protection-cancel or TradeResult evidence.
"""
import json
from datetime import datetime

from application.trading.admission import RuntimeAdmissionError
from application.trading.close_owner import original_entry
from application.trading.position_observation import require_position_read
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_state import restore_product_readback
from brokers.paper_state import decode_fact
from execution.models import OrderRequest,OrderResult,Fill
from position.close_observation import build_product_close_projection
from position.lifecycle_projection import _broker_fact_payload
from position import build_position_lifecycle_execution_evidence_binding
from registry.product_assessment import canonical
from storage.product_position import ProductCloseObservation,observation_material


def project_close_position(service,operation_id,value,*,metadata,proof,expected_revision):
    from application.trading.service import TradingOutcome
    require_position_read(service,value,metadata=metadata,proof=proof,expected_revision=expected_revision)
    service.recover_publications()
    generation=service.dispatch.claim_inventory_generation()
    operation=service.dispatch.operation(service.run_id,operation_id)
    if operation is None or operation.recovery_disposition!='READBACK_REQUIRED':
        raise RuntimeAdmissionError('NATIVE_CLOSE_ORIGINAL_CLAIM_REQUIRED')
    prepared=restore_product_readback(operation.request);request=prepared.canonical_request
    if prepared.role not in ('POSITION_EXIT','EMERGENCY_EXIT'):
        raise RuntimeAdmissionError('NATIVE_CLOSE_ORIGINAL_CLAIM_REQUIRED')
    entry_operation,entry,_,original=original_entry(service,request.trade_plan_id)
    if value.provider_position_id!=original['provider_position_id']:
        raise RuntimeAdmissionError('ORIGINAL_NATIVE_POSITION_LINEAGE_REQUIRED')
    for claimed in service.dispatch.iter_claimed_closes_for_position(service.run_id,request.position_id):
        if (claimed.run_id,claimed.operation_id)!=(service.run_id,operation_id):
            raise RuntimeAdmissionError('PRIOR_ACCOUNT_CLOSE_RECONCILIATION_REQUIRED')
    saved=service.dispatch.position_publication(service.run_id,operation_id,value.received_at)
    outcome=TradingOutcome(operation_id,'CLOSE_POSITION_PROJECTED','ACTUAL_E4_E5_CLOSE_POSITION_OBSERVATION')
    if saved is not None:
        material=json.loads(saved.observation_json)
        if (material.get('profile')!='product-close-native-observation-v0.2' or
                material.get('position')!=observation_material(value) or
                material.get('entry_operation_id')!=entry_operation.operation_id):
            raise RuntimeAdmissionError('NATIVE_CLOSE_EQUAL_TIME_SUBJECT_CONFLICT')
        service.dispatch.require_claim_inventory_generation(generation)
        return outcome
    # An added actual close result invalidates the old execution interpretation.
    # Take the same plan/risk snapshot used by the entry observation adapter,
    # then fence the complete recovered graph, including the exact old action.
    subject=service.canonical.current_execution_subject(service.identity,request.trade_plan_id)
    recovered=service.canonical.recover(trade_plan_id=request.trade_plan_id,position_id=request.position_id)
    reinterpret=(recovered.status=='REINTERPRETATION_REQUIRED' and
        recovered.reason_codes==('E5_EXECUTION_REINTERPRETATION_REQUIRED',) and
        recovered.current_lifecycle_execution_binding is not None)
    if not (recovered.restart_authoritative or reinterpret) or recovered.current_position_projection is None:
        raise RuntimeAdmissionError('NATIVE_CLOSE_CANONICAL_RECONCILIATION_REQUIRED')
    actions=[row.payload for row in recovered.position_actions if row.canonical_id==request.position_action_id]
    sources=[row.payload for row in recovered.lifecycle_history
        if canonical_okx_close_sizing_hash(row.payload)==prepared.source_position_hash]
    if (len(sources)!=1 or len(actions)!=1 or
            prepared.source_plan_hash!=canonical_okx_close_sizing_hash(subject.approved_trade_plan.payload) or
            prepared.source_action_hash!=canonical_okx_close_sizing_hash(actions[0])):
        raise RuntimeAdmissionError('NATIVE_CLOSE_EXACT_ORIGINAL_E5_SUBJECT_REQUIRED')
    source=sources[0];previous=recovered.current_position_projection.payload
    requests=tuple(decode_fact(OrderRequest,row.payload) for row in recovered.order_requests)
    results=tuple(decode_fact(OrderResult,row.payload) for row in recovered.order_result_observations)
    fills=tuple(decode_fact(Fill,row.payload) for row in recovered.fills)
    if any(row.order_role in ('POSITION_EXIT','EMERGENCY_EXIT') and row.order_request_id!=operation_id for row in requests):
        raise RuntimeAdmissionError('NATIVE_CLOSE_SINGLE_ORIGINAL_CLOSE_REQUIRED')
    entry_fills=tuple(row for row in fills if row.client_order_id==entry.canonical_request.client_order_id)
    exit_fills=tuple(row for row in fills if row.client_order_id==request.client_order_id)
    if (len(fills)!=len(entry_fills)+len(exit_fills) or not exit_fills
            or value.provider_updated_at<max(row.filled_at for row in exit_fills)):
        raise RuntimeAdmissionError('NATIVE_CLOSE_COMPLETE_CURRENT_FILL_LINEAGE_REQUIRED')
    latest={row.payload['order_request_id']:decode_fact(OrderResult,row.payload) for row in recovered.current_order_results}
    source_at=datetime.fromisoformat(source['broker_state_observed_at'].replace('Z','+00:00'))
    # Revalidate the original basis against the actual result known at that
    # source anchor. A later identical readback keeps its real later timestamp
    # and remains in the complete execution history below.
    entry_result=max((row for row in results if row.order_request_id==entry.canonical_request.order_request_id
        and row.observed_at<=source_at),key=lambda row:row.observed_at,default=None)
    exit_result=latest.get(operation_id)
    if entry_result is None or exit_result is None:
        raise RuntimeAdmissionError('NATIVE_CLOSE_ACTUAL_ORDER_RESULTS_REQUIRED')
    composed=build_product_close_projection(subject.approved_trade_plan.payload,actions[0],
        entry.canonical_request,entry_result,entry_fills,request,exit_result,exit_fills,value.exposure,
        source_position=source,previous_projection=previous,observed_at=value.received_at)
    final=composed.projections[-1].lifecycle_projection
    effects=[dict(kind='RAW_POSITION',payload=dict(_broker_fact_payload(final),lifecycle_state=final['lifecycle_state']))]
    for item in composed.projections:
        projection=item.lifecycle_projection
        # Preserve every actual reduction-order observation, including pending
        # or canceled protection orders, in the existing complete E5 binding.
        binding=build_position_lifecycle_execution_evidence_binding(projection,
            order_requests=requests,order_results=results,fills=fills)
        effects.extend([dict(kind='POSITION_PROJECTION',payload=projection),dict(kind='LIFECYCLE_EXECUTION_BINDING',payload=binding)])
    observation=ProductCloseObservation(value,entry_operation.operation_id,canonical(source),previous['lifecycle_projection_id'])
    require_position_read(service,value,metadata=metadata,proof=proof,expected_revision=expected_revision)
    service.canonical.require_current_execution_subject(subject)
    if service.canonical.recover(trade_plan_id=request.trade_plan_id,position_id=request.position_id)!=recovered:
        raise RuntimeAdmissionError('NATIVE_CLOSE_CANONICAL_SUBJECT_CHANGED')
    service.dispatch.observe_position(service.run_id,operation_id,observation,effects,lease=service.lease,now=service.clock(),
        claim_inventory_generation=generation)
    service.recover_publications()
    return outcome
