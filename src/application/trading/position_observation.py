"""Current issuer-bound E4 reads, actual E5 entry projection, E6 durable replay.

There is no caller-provided PASS, alternate position state machine, simulation
checkpoint or native ID in canonical financial objects. Reading does not submit.
"""
from datetime import timedelta
import json
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_position import ProductPositionObservation,parse_product_position_response
from brokers.okx_product_state import restore_product_readback
from brokers.paper_state import decode_fact
from execution.models import OrderRequest,OrderResult,Fill
from position.entry_observation import build_product_entry_projection,product_entry_position_id
from position.lifecycle_projection import _broker_fact_payload
from position import build_position_lifecycle_execution_evidence_binding
from storage.product_position import observation_material
from registry.product_assessment import canonical
from application.trading.admission import RuntimeAdmissionError
from application.trading.provider import ProductionProductProvider
from brokers.okx_production_transport import _query


def read_position(service,*,metadata,proof,expected_revision,expected_provider_position_id=None):
    now=service.clock()
    service.translator.capabilities.require(proof,metadata,role='READ_ONLY_RECONCILIATION',now=now)
    if type(service.provider) is ProductionProductProvider and proof.account_hash!=service.provider.account_hash:
        raise RuntimeAdmissionError('EXACT_NATIVE_POSITION_ACCOUNT_REQUIRED')
    query=dict(instId='BTC-USDT-SWAP')
    if expected_provider_position_id is not None:query['posId']=expected_provider_position_id
    _query('/api/v5/account/positions',query)
    response=service._read('/api/v5/account/positions',query,expected_revision)
    received=service.clock()
    value=parse_product_position_response(response,metadata=metadata,request_started_at=now,received_at=received,
        expected_provider_position_id=expected_provider_position_id)
    service.translator.capabilities.require(proof,metadata,role='READ_ONLY_RECONCILIATION',now=service.clock())
    service._guard(expected_revision,'MANAGE_EXISTING')
    service._position_reads={key:record for key,record in service._position_reads.items()
        if record[0].received_at+timedelta(seconds=5)>service.clock()}
    if len(service._position_reads)>=1024:raise RuntimeAdmissionError('NATIVE_POSITION_READ_ISSUANCE_LIMIT')
    service._position_reads[id(value)]=(value,canonical_okx_close_sizing_hash(value),service.lease,service.provider)
    return value


def require_position_read(service,value,*,metadata,proof,expected_revision):
    record=service._position_reads.get(id(value));now=service.clock()
    if (type(value) is not ProductPositionObservation or record is None or record[0] is not value or
        record[1]!=canonical_okx_close_sizing_hash(value) or record[2]!=service.lease or record[3] is not service.provider or
        value.metadata_hash!=canonical_okx_close_sizing_hash(metadata) or not value.received_at<=now<value.received_at+timedelta(seconds=5)):
        raise RuntimeAdmissionError('CURRENT_ISSUER_NATIVE_POSITION_READ_REQUIRED')
    service.translator.capabilities.require(proof,metadata,role='READ_ONLY_RECONCILIATION',now=now)
    service._guard(expected_revision,'MANAGE_EXISTING')
    return value


def project_entry_position(service,operation_id,value,*,metadata,proof,expected_revision):
    from application.trading.service import TradingOutcome
    require_position_read(service,value,metadata=metadata,proof=proof,expected_revision=expected_revision)
    service.recover_publications()
    operation=service.dispatch.operation(service.run_id,operation_id)
    if operation is None or operation.recovery_disposition!='READBACK_REQUIRED':
        raise RuntimeAdmissionError('NATIVE_POSITION_ORIGINAL_ENTRY_CLAIM_REQUIRED')
    prepared=restore_product_readback(operation.request);request=prepared.canonical_request
    if prepared.role!='ENTRY':raise RuntimeAdmissionError('NATIVE_POSITION_ORIGINAL_ENTRY_CLAIM_REQUIRED')
    saved=service.dispatch.position_publication(service.run_id,operation_id,value.received_at)
    outcome=TradingOutcome(operation_id,'POSITION_PROJECTED','ACTUAL_E4_E5_POSITION_OBSERVATION')
    if saved is not None:
        if saved.observation_json!=canonical(observation_material(value)):
            raise RuntimeAdmissionError('NATIVE_POSITION_EQUAL_TIME_SUBJECT_CONFLICT')
        return outcome  # Original receipt is history, not a renewed observation.
    latest=service.dispatch.latest_position_publication(service.run_id,operation_id)
    if latest is not None:
        original=json.loads(latest.observation_json);material=observation_material(value)
        if (original['provider_position_id']!=value.provider_position_id or material['received_at']<latest.observed_at or
            material['provider_updated_at']<original['provider_updated_at']):
            raise RuntimeAdmissionError('ORIGINAL_NATIVE_POSITION_LINEAGE_REQUIRED')
    subject=service.canonical.current_execution_subject(service.identity,request.trade_plan_id)
    if prepared.source_plan_hash!=canonical_okx_close_sizing_hash(subject.approved_trade_plan.payload):
        raise RuntimeAdmissionError('NATIVE_POSITION_ORIGINAL_PLAN_REQUIRED')
    recovered=service.canonical.recover(trade_plan_id=request.trade_plan_id,position_id=product_entry_position_id(request.trade_plan_id))
    previous=None if recovered.current_position_projection is None else recovered.current_position_projection.payload
    reinterpret=(recovered.status=='REINTERPRETATION_REQUIRED' and
        recovered.reason_codes==('E5_EXECUTION_REINTERPRETATION_REQUIRED',) and
        recovered.current_lifecycle_execution_binding is not None)
    if recovered.status=='CONFLICT' or previous is not None and not (recovered.restart_authoritative or reinterpret):
        raise RuntimeAdmissionError('NATIVE_POSITION_CANONICAL_RECONCILIATION_REQUIRED')
    requests=tuple(decode_fact(OrderRequest,item.payload) for item in recovered.order_requests)
    results=tuple(decode_fact(OrderResult,item.payload) for item in recovered.order_result_observations)
    fills=tuple(decode_fact(Fill,item.payload) for item in recovered.fills)
    current=next((decode_fact(OrderResult,item.payload) for item in recovered.current_order_results
                  if item.payload['order_request_id']==request.order_request_id),None)
    entry_fills=tuple(fill for fill in fills if fill.client_order_id==request.client_order_id)
    if (current is None or not entry_fills or value.average_entry_price!=current.average_fill_price or
        value.provider_updated_at<max(fill.filled_at for fill in entry_fills)):
        raise RuntimeAdmissionError('NATIVE_POSITION_ENTRY_SOURCE_NOT_CONVERGED')
    composed=build_product_entry_projection(subject.approved_trade_plan.payload,request,current,entry_fills,value.exposure,
        observed_at=value.received_at,previous_projection=previous)
    raw=dict(_broker_fact_payload(composed.projections[-1].lifecycle_projection),
        lifecycle_state=composed.projections[-1].lifecycle_projection['lifecycle_state'])
    effects=[dict(kind='RAW_POSITION',payload=raw)]
    for item in composed.projections:
        projection=item.lifecycle_projection
        # Complete canonical history is used, including reduction observations;
        # no latest-only snapshot or broker simulation checkpoint is substituted.
        binding=build_position_lifecycle_execution_evidence_binding(projection,
            order_requests=requests,order_results=results,fills=fills)
        effects.extend([dict(kind='POSITION_PROJECTION',payload=projection),dict(kind='LIFECYCLE_EXECUTION_BINDING',payload=binding)])
    require_position_read(service,value,metadata=metadata,proof=proof,expected_revision=expected_revision)
    service.canonical.require_current_execution_subject(subject)
    service.dispatch.observe_position(service.run_id,operation_id,value,effects,lease=service.lease,now=service.clock())
    service.recover_publications()
    return outcome
