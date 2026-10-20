"""Issuer-bound explicit close composition; no default real account profile.

The fixed fixture close constraints are independent of entry min/max metadata.
They are engineering simulation inputs, never evidence of provider applicability.
Actual E5 action, native read ownership, FP04, metadata/capability and current
E6/E7 gates still apply. Preparing does not dispatch or change lifecycle state.
"""
from datetime import datetime,timedelta
from decimal import Decimal
import json

from application.trading.admission import RuntimeAdmissionError
from application.trading.position_observation import require_position_read
from application.trading.provider import FakeProductProvider
from brokers.okx_product_state import restore_product_readback
from brokers.okx_close_sizing import (OKXCloseSizingInput,OKXProviderExposureObservation,
    OKXCloseMetadataApplicabilityEvidence,canonical_okx_close_sizing_hash)
from brokers.okx_close_sizing_binding import OKXCloseMetadataBindingEvidence
from execution.external_close_evidence import (OwnershipEvaluationContext,ProviderObjectObservation,
    build_external_provider_ownership_evidence,canonical_evidence_hash)
from position import authorize_close_position_action
from position.entry_observation import product_entry_position_id
from storage.product_position import observation_material


def _stamp(value):return value.isoformat().replace('+00:00','Z')


def original_entry(service,trade_plan_id):
    found=[]
    for operation in service.dispatch.iter_claimed_entries_for_account(service.run_id):
        try:prepared=restore_product_readback(operation.request)
        except ValueError:raise RuntimeAdmissionError('NATIVE_CLOSE_ACCOUNT_POSITION_OWNERSHIP_UNKNOWN') from None
        request=prepared.canonical_request
        if request.trade_plan_id==trade_plan_id:
            if operation.run_id!=service.run_id:raise RuntimeAdmissionError('ORIGINAL_NATIVE_CLOSE_ENTRY_OWNER_REQUIRED')
            found.append((operation,prepared))
        else:
            recovered=service.canonical.recover(trade_plan_id=request.trade_plan_id)
            rejected=(recovered.status!='CONFLICT' and not recovered.fills and recovered.current_order_results
                and all(row.payload['order_status']=='REJECTED' and Decimal(row.payload['filled_quantity'])==0 for row in recovered.current_order_results))
            closed=(recovered.restart_authoritative and recovered.trade_result is not None
                and recovered.current_position_projection is not None and recovered.current_position_projection.payload['lifecycle_state']=='CLOSED'
                and recovered.current_order_results and all(row.payload['order_status'] in ('FILLED','CANCELED','EXPIRED','REJECTED')
                    for row in recovered.current_order_results))
            if not rejected and not closed:raise RuntimeAdmissionError('NATIVE_CLOSE_ACCOUNT_POSITION_OWNERSHIP_UNKNOWN')
    if len(found)!=1:raise RuntimeAdmissionError('ORIGINAL_NATIVE_CLOSE_ENTRY_OWNER_REQUIRED')
    operation,prepared=found[0]
    published=service.dispatch.latest_position_publication(service.run_id,operation.operation_id)
    if published is None:raise RuntimeAdmissionError('ORIGINAL_NATIVE_POSITION_BINDING_REQUIRED')
    material=json.loads(published.observation_json)
    if material.get('profile')!='okx-product-position-readback-v0.2' or Decimal(material['canonical_net_quantity'])==0:
        raise RuntimeAdmissionError('ORIGINAL_POSITIVE_NATIVE_POSITION_BINDING_REQUIRED')
    return operation,prepared,published,material


def fixture_close_profile(metadata,role):
    policy=dict(profile='fixture-okx-explicit-close-constraints-v0.2',provenance='FIXTURE_ONLY',step='1',minimum='1',maximum=None)
    profile_hash=canonical_evidence_hash(policy);metadata_hash=canonical_okx_close_sizing_hash(metadata)
    applicability=OKXCloseMetadataApplicabilityEvidence(role,'CLOSE_ROLE','fixture-close-profile:'+profile_hash,
        'fixture-close-profile-generation:'+profile_hash,'CURRENT','product-metadata:'+metadata_hash,'LINEAR_DIRECT_BASE_ASSET',
        'REQUIRED_FOR_CLOSE','APPLICABLE_CONSTRAINT','APPLICABLE_CONSTRAINT','NOT_APPLICABLE_TO_CLOSE',Decimal(1),Decimal(1),None)
    binding=OKXCloseMetadataBindingEvidence('fixture-close-binding:'+metadata_hash,metadata.metadata_ref,metadata_hash,
        applicability.instrument_metadata_generation,applicability.applicability_proof_ref,
        canonical_okx_close_sizing_hash(applicability),applicability.applicability_generation_id)
    return applicability,binding


def prepare_fixture_close(service,trade_plan_id,position,*,metadata,read_proof,close_proof,expected_revision,action='EXIT'):
    if service.execution!='FAKE_PROVIDER_VERIFICATION' or type(service.provider) is not FakeProductProvider or service.admission.namespace!='FIXTURE':
        raise RuntimeAdmissionError('FIXTURE_CLOSE_MECHANICAL_PROFILE_ONLY')
    applicability,binding=fixture_close_profile(metadata,'POSITION_EXIT' if action=='EXIT' else 'EMERGENCY_EXIT')
    return prepare_close(service,trade_plan_id,position,metadata=metadata,read_proof=read_proof,close_proof=close_proof,
        expected_revision=expected_revision,action=action,metadata_applicability=applicability,metadata_binding=binding)


def prepare_close(service,trade_plan_id,position,*,metadata,read_proof,close_proof,expected_revision,
                  metadata_applicability,metadata_binding,action='EXIT'):
    # Trusted E4 composition supplies the independently established close-role
    # applicability and its exact binding. No HTTP body/PASS/default supplies it.
    if type(metadata_applicability) is not OKXCloseMetadataApplicabilityEvidence or type(metadata_binding) is not OKXCloseMetadataBindingEvidence:
        raise RuntimeAdmissionError('EXACT_CLOSE_METADATA_APPLICABILITY_BINDING_REQUIRED')
    require_position_read(service,position,metadata=metadata,proof=read_proof,expected_revision=expected_revision)
    service.recover_publications();now=service.clock();generation=service.dispatch.claim_inventory_generation()
    operation,entry,published,original=original_entry(service,trade_plan_id)
    recovered=service.canonical.recover(trade_plan_id=trade_plan_id,position_id=product_entry_position_id(trade_plan_id))
    if not recovered.restart_authoritative or recovered.current_position_projection is None or recovered.current_lifecycle_execution_binding is None:
        raise RuntimeAdmissionError('NATIVE_CLOSE_CURRENT_E5_POSITION_REQUIRED')
    source=recovered.current_position_projection.payload
    signed=Decimal(source['actual_quantity'])*(1 if source['side']=='LONG' else -1)
    entry_fill_times=[datetime.fromisoformat(row.payload['filled_at'].replace('Z','+00:00')) for row in recovered.fills
        if row.payload['client_order_id']==entry.canonical_request.client_order_id]
    if (signed==0 or position.provider_position_id!=original['provider_position_id'] or position.canonical_net_quantity!=signed
            or position.average_entry_price!=Decimal(source['average_entry_price'])
            or not entry_fill_times or position.provider_updated_at<max(entry_fill_times)):
        raise RuntimeAdmissionError('NATIVE_CLOSE_ORIGINAL_CURRENT_POSITION_REQUIRED')
    if any(service.dispatch.iter_claimed_closes_for_position(service.run_id,source['position_id'])):
        raise RuntimeAdmissionError('PRIOR_ACCOUNT_CLOSE_RECONCILIATION_REQUIRED')
    subject=service.canonical.current_execution_subject(service.identity,trade_plan_id);plan=subject.approved_trade_plan.payload
    close=authorize_close_position_action(source,plan,action=action,created_at=now,expires_at=now+timedelta(seconds=30)).position_action
    role='POSITION_EXIT' if action=='EXIT' else 'EMERGENCY_EXIT'
    capability=service.translator.capabilities.close_capability(close_proof,metadata,now=now)
    if capability.action_role!=role:raise RuntimeAdmissionError('EXACT_NATIVE_CLOSE_ROLE_PROOF_REQUIRED')
    decision=service.admission.evaluate(service.identity,expected_revision=expected_revision,permission='MANAGE_EXISTING',execution=service.execution)
    if not decision.allowed:raise RuntimeAdmissionError(*decision.reason_codes)
    release=decision.owner_permission.release;native_material=observation_material(position)
    identity=dict(provider_ref=release.provider_ref,account_ref=release.account_ref,account_hash=close_proof.account_hash)
    provider_ref='product-provider:'+canonical_evidence_hash(identity);read_hash=canonical_evidence_hash(native_material)
    read_generation='product-position-read:'+read_hash;object_ref='OKX:position:'+position.provider_position_id
    observation=ProviderObjectObservation('POSITION_EXPOSURE',provider_ref,identity,'BTC_USDT_PERP','BTC-USDT-SWAP',
        object_ref,'product-position-snapshot:'+read_hash,native_material,read_generation,position.request_started_at,position.received_at)
    lineage=[dict(owner='E4',evidence_class='PRODUCT_ORIGINAL_POSITION_BINDING',evidence_ref=operation.operation_id,
        evidence_hash=published.observation_hash,evidence_generation_id=read_generation,
        observed_or_created_at=_stamp(position.request_started_at),lineage_role='POSITION',claim_status='CLAIMS_OWNERSHIP')]
    registry=[dict(owner='E6',evidence_class='PRODUCT_POSITION_EXECUTION_BINDING',
        evidence_ref=recovered.current_lifecycle_execution_binding.canonical_id,
        evidence_hash=recovered.current_lifecycle_execution_binding.payload_hash,evidence_generation_id=read_generation,
        observed_at=_stamp(position.received_at),currentness_status='CURRENT')]
    context=OwnershipEvaluationContext(release.executable_revision,lineage,registry,'CURRENT_GENERATION','EXACT','SINGLE',now,
        runtime_preflight_ref=decision.preflight_id,runtime_process_instance_id=decision.process_binding[0],
        runtime_process_start_generation_id=decision.process_binding[1],runtime_config_generation_id='config-generation:'+str(release.config_generation))
    ownership=build_external_provider_ownership_evidence(observation,context)
    exposure=OKXProviderExposureObservation(provider_ref,identity,object_ref,'net','product-position-snapshot:'+read_hash,
        native_material,read_generation,position.request_started_at,position.received_at,'CURRENT',
        abs(position.provider_contract_quantity),'CONTRACT',abs(position.canonical_net_quantity),'2','net_mode','isolated')
    value=OKXCloseSizingInput(close,plan,source,source,'PRE_ACTION','CLEAR','no-prior-close:'+canonical_evidence_hash(generation),
        exposure,ownership,context,capability,metadata,metadata_applicability,now)
    prepared=service.translator.prepare_close(value,metadata_binding,close_proof,now=now)
    require_position_read(service,position,metadata=metadata,proof=read_proof,expected_revision=expected_revision)
    service.dispatch.require_claim_inventory_generation(generation)
    service.canonical.require_current_execution_subject(subject)
    if service.canonical.recover(trade_plan_id=trade_plan_id,position_id=source['position_id'])!=recovered:
        raise RuntimeAdmissionError('NATIVE_CLOSE_CANONICAL_SUBJECT_CHANGED')
    service._close_preparations={key:record for key,record in service._close_preparations.items() if record[0].expires_at>now}
    if len(service._close_preparations)>=1024:raise RuntimeAdmissionError('NATIVE_CLOSE_PREPARATION_LIMIT')
    service.canonical.persist_position_action(close)
    service._close_preparations[id(prepared)]=(prepared,position,metadata,read_proof,close_proof,service.lease,service.provider,expected_revision)
    return prepared


def require_close_preparation(service,prepared):
    record=service._close_preparations.get(id(prepared))
    if record is None or record[0] is not prepared or record[5]!=service.lease or record[6] is not service.provider:
        raise RuntimeAdmissionError('ORIGINAL_NATIVE_CLOSE_PREPARATION_REQUIRED')
    _,position,metadata,read_proof,close_proof,_,_,revision=record
    require_position_read(service,position,metadata=metadata,proof=read_proof,expected_revision=revision)
    service.translator.capabilities.require(close_proof,metadata,role=prepared.role,now=service.clock())
    _,_,_,original=original_entry(service,prepared.canonical_request.trade_plan_id)
    if original['provider_position_id']!=position.provider_position_id:
        raise RuntimeAdmissionError('ORIGINAL_NATIVE_POSITION_BINDING_REQUIRED')
