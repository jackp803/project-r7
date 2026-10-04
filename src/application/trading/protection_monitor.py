"""Actual E4 ownership/registry evidence and E5 non-closure projections.

The canonical owners decide every state/event. A native ACK, a row name or a
copy of an inventory never grants protection, adoption, cleanup or another POST.
"""
from datetime import timedelta
from decimal import Decimal
import json

from application.trading.admission import RuntimeAdmissionError
from application.trading.position_observation import require_position_read
from brokers.okx_product_state import restore_product_readback
from brokers.okx_product_readback import parse_product_algo
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.paper_state import decode_fact
from execution.models import OrderRequest,OrderResult,Fill
from execution.external_close_evidence import (ProviderObjectObservation,OwnershipEvaluationContext,
    build_external_provider_ownership_evidence,canonical_evidence_hash)
from execution.protection_registry_evidence import (FP04ActiveProtectionDependency,ProtectionRegistryMultiplicityInput,
    active_protection_set_hash)
from execution.protection_registry_evidence_boundary import build_protection_registry_multiplicity_evidence
from position.protection_result import ProtectionResultEvidence,interpret_protection_result
from position.protection_registry_policy import (CurrentProtectionRegistryAuthority,interpret_protection_registry_evidence,
                                                canonical_protection_registry_hash)
from position.lifecycle_projection import (build_position_lifecycle_transition,build_position_lifecycle_reattestation,
                                          _broker_fact_payload)
from position.lifecycle_execution_binding import build_position_lifecycle_execution_evidence_binding
from registry.product_assessment import canonical
from storage.product_position import (ProductProtectionObservation,observation_material,inventory_material)


def _stamp(value):return value.isoformat().replace('+00:00','Z')


def _registry(service,prepared,operation,position,binding,inventory,decision,results):
    release=decision.owner_permission.release
    generation='product-algo-read:'+canonical_okx_close_sizing_hash(inventory)
    identity=dict(provider_ref=release.provider_ref,account_ref=release.account_ref,account_hash=inventory.account_hash)
    provider_ref='product-provider:'+canonical_evidence_hash(identity)
    instrument='OKX:BTC-USDT-SWAP'
    runtimes=dict(runtime_preflight_ref=decision.preflight_id,runtime_process_instance_id=decision.process_binding[0],
        runtime_process_start_generation_id=decision.process_binding[1],
        runtime_config_generation_id='config-generation:'+str(release.config_generation))
    observation=None if operation.observation_json is None else json.loads(operation.observation_json)
    native=None if observation is None else observation['provider_id']
    request=prepared.canonical_request
    claims=service.dispatch.claimed_protections_for_account(service.run_id)
    claimed_clients={item.request['native_client_id'] for item in claims}
    claimed_provider_ids={json.loads(item.observation_json)['provider_id'] for item in claims if item.observation_json is not None}
    claim_hash=canonical_evidence_hash([dict(run_id=item.run_id,operation_id=item.operation_id,request=item.request,
        observation=None if item.observation_json is None else json.loads(item.observation_json)) for item in claims])
    claim_observed_at=service.clock()
    dependencies=[];entries=[]
    for item in inventory.objects:
        exact=False;owned=False
        try:
            parsed=parse_product_algo(dict(code='0',data=[item.row]),prepared,expected_provider_id=native)
            owned=(native is not None and parsed.status=='ACTIVE' and
                any(result.broker_order_id==native and result.order_status.value=='OPEN' for result in results))
            exact=owned and request.quantity==Decimal(position['actual_quantity'])
        except ValueError:pass
        snapshot=dict(native_row=item.row,source_hash=item.source_hash)
        object_ref='OKX:algo:'+item.provider_algo_id
        observed=ProviderObjectObservation('ACTIVE_PROTECTION',provider_ref,identity,'BTC_USDT_PERP',instrument,
            object_ref,'product-algo-snapshot:'+item.source_hash,snapshot,generation,inventory.request_started_at,inventory.received_at)
        lineage=[]
        if owned:
            lineage=[dict(owner='E4',evidence_class='PRODUCT_ORIGINAL_ORDER_REQUEST',evidence_ref=request.order_request_id,
                evidence_hash=canonical_protection_registry_hash(request),evidence_generation_id=generation,
                observed_or_created_at=_stamp(request.created_at),lineage_role='ORDER_REQUEST',claim_status='CLAIMS_OWNERSHIP')]
        local=[dict(owner='E6',evidence_class='PRODUCT_ACCOUNT_PROTECTION_CLAIM_INVENTORY',
            evidence_ref='product-account-protection-claims:'+claim_hash,evidence_hash=claim_hash,
            evidence_generation_id=generation,observed_at=_stamp(claim_observed_at),currentness_status='CURRENT')]
        known_elsewhere=(item.row.get('algoClOrdId') in claimed_clients or item.provider_algo_id in claimed_provider_ids)
        lineage_status=('CURRENT_GENERATION' if owned else
                        'UNKNOWN' if known_elsewhere or not item.row.get('algoClOrdId') else 'EXTERNAL')
        context=OwnershipEvaluationContext(release.executable_revision,lineage,local,
            lineage_status,'EXACT','SINGLE',service.clock(),**runtimes)
        evidence=build_external_provider_ownership_evidence(observed,context)
        dependency=FP04ActiveProtectionDependency(observed,context,evidence);dependencies.append(dependency)
        material=dict(original_request_hash=canonical_protection_registry_hash(request),source_position_hash=canonical_evidence_hash(position),
            provider_object_ref=object_ref,exact_current_quantity=exact,source_hash=item.source_hash)
        entries.append(dict(provider_object_ref=object_ref,provider_snapshot_ref=evidence['provider_snapshot_ref'],
            provider_snapshot_hash=evidence['provider_snapshot_hash'],provider_object_observed_at=evidence['provider_observed_at'],
            ownership_evidence_ref=evidence['ownership_evidence_id'],ownership_evidence_hash=canonical_evidence_hash(evidence),
            ownership_classification=evidence['ownership_classification'],ownership_reconciliation_status=evidence['reconciliation_status'],
            intended_lineage_binding_status='EXACT_MATCH' if exact else 'NOT_MATCH',
            intended_lineage_binding_ref='product-stop-binding:'+canonical_evidence_hash(material),
            intended_lineage_binding_hash=canonical_evidence_hash(material)))
    position_ref='position:'+position['position_id']+'@'+position['broker_state_observed_at']
    lineage=dict(position_ref=position_ref,position_hash=canonical_protection_registry_hash(position),
        position_id=position['position_id'],position_observed_at=position['broker_state_observed_at'],position_side=position['side'],
        position_quantity_ref=position_ref+':actual_quantity',position_action_ref=request.position_action_id,
        position_action_hash=prepared.source_action_hash,position_action_id=request.position_action_id,
        approved_trade_plan_ref=request.trade_plan_id,approved_trade_plan_hash=prepared.source_plan_hash,
        risk_decision_ref=request.risk_decision_id,protection_order_request_ref=request.order_request_id,
        protection_order_request_hash=canonical_protection_registry_hash(request),client_order_identity_ref=request.client_order_id,
        lifecycle_projection_ref=position['lifecycle_projection_id'],
        lifecycle_execution_binding_ref=binding['lifecycle_execution_binding_id'],trigger_validity_ref=None,
        ownership_reconciliation_generation_ref=generation,**runtimes)
    observed_set=dict(provider_identity_ref=provider_ref,provider_identity_hash=canonical_evidence_hash(identity),
        canonical_symbol='BTC_USDT_PERP',provider_instrument_ref=instrument,provider_observation_generation_id=generation,
        provider_observed_at=_stamp(inventory.request_started_at),provider_received_at=_stamp(inventory.received_at),
        observation_coverage_status='COMPLETE',set_currentness_status='CURRENT',objects=entries)
    observed_set['observed_set_hash']=active_protection_set_hash(observed_set)
    evidence=build_protection_registry_multiplicity_evidence(ProtectionRegistryMultiplicityInput(position_ref,position,lineage,
        observed_set,tuple(dependencies),service.clock(),lifecycle_projection_ref=position['lifecycle_projection_id'],
        lifecycle_execution_binding_ref=binding['lifecycle_execution_binding_id'],**runtimes))
    authority=CurrentProtectionRegistryAuthority(position_ref,evidence['position_hash'],position,position,binding,provider_ref,
        instrument,generation,evidence['provider_observed_at'],evidence['provider_received_at'],
        evidence['observed_active_protection_set_hash'],**runtimes)
    return evidence,interpret_protection_registry_evidence(evidence,authority),[item.evidence for item in dependencies]


def project_protection(service,operation_id,position_read,inventory,*,metadata,proof,expected_revision):
    from application.trading.service import TradingOutcome
    require_position_read(service,position_read,metadata=metadata,proof=proof,expected_revision=expected_revision)
    service.require_algo_inventory(inventory,metadata=metadata,proof=proof,expected_revision=expected_revision)
    service.recover_publications()
    operation=service.dispatch.operation(service.run_id,operation_id)
    if operation is None or operation.recovery_disposition!='READBACK_REQUIRED':
        raise RuntimeAdmissionError('ORIGINAL_PROTECTION_DISPATCH_CLAIM_REQUIRED')
    prepared=restore_product_readback(operation.request);request=prepared.canonical_request
    if prepared.role!='PROTECTION_STOP':raise RuntimeAdmissionError('ORIGINAL_PROTECTION_DISPATCH_CLAIM_REQUIRED')
    saved=service.dispatch.position_publication(service.run_id,operation_id,inventory.received_at)
    if saved is not None:
        original=json.loads(saved.observation_json)
        if original.get('position')!=observation_material(position_read) or original.get('inventory')!=inventory_material(inventory):
            raise RuntimeAdmissionError('PROTECTION_EQUAL_TIME_SUBJECT_CONFLICT')
        return TradingOutcome(operation_id,'PROTECTION_PROJECTED',original['reason_code'])
    subject=service.canonical.current_execution_subject(service.identity,request.trade_plan_id,
        position_id=request.position_id,position_action_id=request.position_action_id)
    recovered=service.canonical.recover(position_id=request.position_id,trade_plan_id=request.trade_plan_id)
    previous=subject.current_position_projection.payload
    if (prepared.source_plan_hash!=canonical_okx_close_sizing_hash(subject.approved_trade_plan.payload) or
        prepared.source_action_hash!=canonical_okx_close_sizing_hash(subject.position_action.payload) or
        not any(canonical_okx_close_sizing_hash(item.payload)==prepared.source_position_hash for item in recovered.lifecycle_history) or
        Decimal(previous['actual_quantity'])!=abs(position_read.canonical_net_quantity) or
        Decimal(previous['average_entry_price'])!=position_read.average_entry_price or
        previous['broker_state_observed_at']!=_stamp(position_read.received_at) or
        not position_read.received_at<=inventory.request_started_at):
        raise RuntimeAdmissionError('EXACT_CURRENT_NATIVE_PROTECTION_POSITION_REQUIRED')
    requests=tuple(decode_fact(OrderRequest,item.payload) for item in recovered.order_requests)
    results=tuple(decode_fact(OrderResult,item.payload) for item in recovered.order_result_observations)
    fills=tuple(decode_fact(Fill,item.payload) for item in recovered.fills)
    current=next((decode_fact(OrderResult,item.payload) for item in recovered.current_order_results
        if item.payload['order_request_id']==operation_id),None)
    queried=(current is not None and current.observed_at<=inventory.request_started_at<current.observed_at+timedelta(seconds=5) and
        operation.observation_json is not None and json.loads(operation.observation_json)['status']=='ALGO_OBSERVED')
    interpreted=interpret_protection_result(request,ProtectionResultEvidence(queried,queried_order=current if queried else None),
        previous['lifecycle_state'])
    source=dict(_broker_fact_payload(previous),lifecycle_state=previous['lifecycle_state'])
    candidate=previous
    if interpreted.protection_verified and interpreted.event is not None:
        candidate=build_position_lifecycle_transition(source,previous,lifecycle_event=interpreted.event,
            lifecycle_interpreted_at=service.clock())
    binding=build_position_lifecycle_execution_evidence_binding(candidate,order_requests=requests,order_results=results,fills=fills)
    decision=service.admission.evaluate(service.identity,expected_revision=expected_revision,
        permission='MANAGE_EXISTING',execution=service.execution)
    if not decision.allowed:raise RuntimeAdmissionError(*decision.reason_codes)
    evidence,registry,dependencies=_registry(service,prepared,operation,candidate,binding,inventory,decision,
        () if not queried else (current,))
    if interpreted.protection_verified and not registry.healthy_protection and candidate is not previous:
        # A rejected candidate never became canonical protection. Reinterpret
        # FP11 against the actual original lifecycle/binding; a missing set
        # cannot fall back to the discarded PROTECTION_VERIFIED event.
        evidence,registry,dependencies=_registry(service,prepared,operation,previous,
            subject.current_lifecycle_execution_binding.payload,inventory,decision,() if not queried else (current,))
    if interpreted.protection_verified:
        event=interpreted.event if registry.healthy_protection else registry.event
        reason=interpreted.reason_code if registry.healthy_protection else registry.reason_codes[0]
    elif registry.decision=='RECONCILE':event=registry.event;reason=registry.reason_codes[0]
    else:event=interpreted.event;reason=interpreted.reason_code
    if event is None:
        projection=build_position_lifecycle_reattestation(source,previous,lifecycle_interpreted_at=service.clock())
    else:
        projection=build_position_lifecycle_transition(source,previous,lifecycle_event=event,lifecycle_interpreted_at=service.clock())
    final_binding=build_position_lifecycle_execution_evidence_binding(projection,order_requests=requests,order_results=results,fills=fills)
    raw=next((item.payload for item in recovered.raw_position_observations
        if item.payload['broker_state_observed_at']==previous['broker_state_observed_at']),None)
    if raw is None:raise RuntimeAdmissionError('ORIGINAL_RAW_POSITION_OBSERVATION_REQUIRED')
    effects=[dict(kind='RAW_POSITION',payload=raw),dict(kind='POSITION_PROJECTION',payload=projection),
             dict(kind='LIFECYCLE_EXECUTION_BINDING',payload=final_binding)]
    observation=ProductProtectionObservation(position_read,inventory,previous['lifecycle_projection_id'],
        canonical(dependencies),canonical(evidence),reason)
    require_position_read(service,position_read,metadata=metadata,proof=proof,expected_revision=expected_revision)
    service.require_algo_inventory(inventory,metadata=metadata,proof=proof,expected_revision=expected_revision)
    service.canonical.require_current_execution_subject(subject)
    service.dispatch.observe_position(service.run_id,operation_id,observation,effects,lease=service.lease,now=service.clock())
    service.recover_publications()
    return TradingOutcome(operation_id,'PROTECTION_PROJECTED',reason)
