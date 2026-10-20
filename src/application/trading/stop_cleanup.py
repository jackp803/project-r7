"""Exact unused owned stop after original flat; controlled FIXTURE profile only."""
from dataclasses import dataclass,replace
from datetime import datetime,timedelta
from decimal import Decimal
import json

from application.trading.admission import RuntimeAdmissionError
from application.trading.funding_owner import _fixture,_context
from application.trading.position_observation import require_position_read
from application.trading.algo_inventory import require_algo_inventory
from application.trading.provider import ProductProviderError
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_state import restore_product_readback
from brokers.okx_product_readback import parse_product_algo
from brokers.okx_product_inventory import parse_product_algo_page
from registry.product_assessment import canonical
from storage.product_dispatch import _read
from storage.product_position import observation_material,inventory_material


@dataclass(frozen=True)
class ProductCleanupStopRead:
    operation_id:str
    native_algo_id:str
    status:str
    request_started_at:datetime
    received_at:datetime
    row_json:str
    source_hash:str


def read_fixture_cleanup_stop(service,operation_id,*,expected_revision):
    _fixture(service);service._guard(expected_revision,'MANAGE_EXISTING')
    lease,provider=service.lease,service.provider
    operation=service.dispatch.operation(service.run_id,operation_id)
    if operation is None or operation.recovery_disposition!='READBACK_REQUIRED':
        raise RuntimeAdmissionError('CLEANUP_ORIGINAL_STOP_CLAIM_REQUIRED')
    prepared=restore_product_readback(operation.request)
    observation={} if operation.observation_json is None else json.loads(operation.observation_json)
    native=observation.get('provider_id')
    if prepared.role!='PROTECTION_STOP' or native is None:
        raise RuntimeAdmissionError('CLEANUP_ORIGINAL_NATIVE_STOP_REQUIRED')
    started=service.clock()
    response=service._read('/api/v5/trade/order-algo',dict(algoId=native),expected_revision)
    received=service.clock()
    parsed=parse_product_algo(response,prepared,expected_provider_id=native)
    rows=parse_product_algo_page(response,algo_type=prepared.materialization.body['ordType'],received_at=received)
    if len(rows)!=1 or parsed.provider_algo_id!=native or rows[0].provider_algo_id!=native:
        raise RuntimeAdmissionError('CLEANUP_EXACT_TARGET_READ_REQUIRED')
    service._guard(expected_revision,'MANAGE_EXISTING')
    if service.lease!=lease or service.provider is not provider or not started<=service.clock()<started+timedelta(seconds=5):
        raise RuntimeAdmissionError('CLEANUP_CURRENT_ORIGINAL_READ_ISSUER_REQUIRED')
    row=rows[0];value=ProductCleanupStopRead(operation_id,native,parsed.status,started,received,row.row_json,row.source_hash)
    service._cleanup_stop_reads={key:record for key,record in service._cleanup_stop_reads.items()
        if record[0].request_started_at+timedelta(seconds=5)>service.clock()}
    if len(service._cleanup_stop_reads)>=128:raise RuntimeAdmissionError('CLEANUP_READ_ISSUANCE_LIMIT')
    service._cleanup_stop_reads[id(value)]=(value,canonical_okx_close_sizing_hash(value),lease,provider)
    return value


def _require_stop_read(service,value,operation_id):
    record=service._cleanup_stop_reads.get(id(value));now=service.clock()
    if (type(value) is not ProductCleanupStopRead or record is None or record[0] is not value or
            value.operation_id!=operation_id or record[1]!=canonical_okx_close_sizing_hash(value) or
            record[2]!=service.lease or record[3] is not service.provider or
            not value.request_started_at<=now<value.request_started_at+timedelta(seconds=5)):
        raise RuntimeAdmissionError('CLEANUP_CURRENT_ORIGINAL_TARGET_READ_REQUIRED')


@dataclass(frozen=True)
class _StopCleanupPreparation:
    stop_operation_id:str
    native_algo_id:str
    close_operation_id:str
    flat_publication_hash:str
    created_at:datetime


def _source(service,operation_id,target,native,inventory,metadata,proof,revision):
    _fixture(service);_require_stop_read(service,target,operation_id)
    require_position_read(service,native,metadata=metadata,proof=proof,expected_revision=revision)
    require_algo_inventory(service,inventory,metadata=metadata,proof=proof,expected_revision=revision)
    operation=service.dispatch.operation(service.run_id,operation_id)
    if operation is None or operation.recovery_disposition!='READBACK_REQUIRED':
        raise RuntimeAdmissionError('CLEANUP_ORIGINAL_STOP_CLAIM_REQUIRED')
    stop=restore_product_readback(operation.request);request=stop.canonical_request
    if stop.role!='PROTECTION_STOP':raise RuntimeAdmissionError('CLEANUP_ORIGINAL_STOP_CLAIM_REQUIRED')
    context=_context(service,request.trade_plan_id,request.position_id,revision)
    claims=tuple(service.dispatch.iter_claimed_initial_protections_for_position(service.run_id,request.position_id))
    if len(claims)!=1 or (claims[0].run_id,claims[0].operation_id)!=(service.run_id,operation_id):
        raise RuntimeAdmissionError('CLEANUP_SINGLE_ORIGINAL_STOP_REQUIRED')
    recovered=context.recovered
    current={item.payload['order_request_id']:item.payload for item in recovered.current_order_results}
    if (set(current)!={item.payload['order_request_id'] for item in recovered.order_requests} or
            current.get(operation_id,{}).get('order_status')!='OPEN' or
            any(result['order_status'] not in ('FILLED','CANCELED','EXPIRED','REJECTED') for key,result in current.items() if key!=operation_id) or
            any(row.payload['order_request_id']==operation_id for row in recovered.order_requests
                if row.payload!=json.loads(operation.request_json)['canonical_request']) or
            any(row.payload['client_order_id']==request.client_order_id for row in recovered.fills)):
        raise RuntimeAdmissionError('CLEANUP_SETTLED_ENTRY_AND_CLOSE_WITH_UNUSED_STOP_REQUIRED')
    actions=[item.payload for item in recovered.position_actions if item.canonical_id==request.position_action_id]
    if (stop.source_plan_hash!=canonical_okx_close_sizing_hash(context.execution_subject.approved_trade_plan.payload) or
            len(actions)!=1 or canonical_okx_close_sizing_hash(actions[0])!=stop.source_action_hash):
        raise RuntimeAdmissionError('CLEANUP_ORIGINAL_E5_STOP_LINEAGE_REQUIRED')
    verified=service.dispatch.latest_position_publication(service.run_id,operation_id)
    if verified is None:raise RuntimeAdmissionError('CLEANUP_ORIGINAL_VERIFIED_STOP_REQUIRED')
    original=_read(verified.observation_json,verified.observation_hash)
    if (original.get('profile')!='product-protection-observation-v0.2' or
            verified.effects[-2]['payload']['lifecycle_state'] not in ('OPEN_PROTECTED','PROFIT_PROTECTED') or
            original['inventory']['account_hash']!=inventory.account_hash):
        raise RuntimeAdmissionError('CLEANUP_ORIGINAL_VERIFIED_STOP_REQUIRED')
    objects=[row for row in original['inventory']['objects'] if row['provider_algo_id']==target.native_algo_id]
    flat_native=json.loads(context.flat_publication.observation_json)['position']
    flat_at=datetime.fromisoformat(context.flat_publication.observed_at.replace('Z','+00:00'))
    if (len(objects)!=1 or len(inventory.objects)!=1 or target.status!='ACTIVE' or
            native.provider_position_id!=context.source_subject.native_position_id or native.canonical_net_quantity!=0 or
            native.provider_updated_at<datetime.fromisoformat(flat_native['provider_updated_at'].replace('Z','+00:00')) or
            any(start<flat_at for start in (target.request_started_at,native.request_started_at,inventory.request_started_at))):
        raise RuntimeAdmissionError('CLEANUP_CURRENT_EXACT_UNUSED_TARGET_AND_FLAT_REQUIRED')
    row=inventory.objects[0]
    parsed=parse_product_algo(dict(code='0',data=[row.row]),stop,expected_provider_id=target.native_algo_id)
    if (parsed.status!='ACTIVE' or row.provider_algo_id!=target.native_algo_id or row.source_hash!=target.source_hash or
            row.provider_created_at!=datetime.fromisoformat(objects[0]['provider_created_at'].replace('Z','+00:00'))):
        raise RuntimeAdmissionError('CLEANUP_TARGET_AND_FULL_INVENTORY_DISAGREE')
    service.dispatch.require_claim_inventory_generation(context.generation)
    return context,verified


def prepare_fixture_stop_cleanup(service,operation_id,target,native,inventory,*,metadata,proof,expected_revision):
    context,verified=_source(service,operation_id,target,native,inventory,metadata,proof,expected_revision)
    value=_StopCleanupPreparation(operation_id,target.native_algo_id,context.close_operation.operation_id,
        context.flat_publication.observation_hash,service.clock())
    service._stop_cleanup_preparations={key:record for key,record in service._stop_cleanup_preparations.items()
        if record[0].created_at+timedelta(seconds=5)>service.clock()}
    if len(service._stop_cleanup_preparations)>=128:raise RuntimeAdmissionError('CLEANUP_PREPARATION_LIMIT')
    service._stop_cleanup_preparations[id(value)]=(value,canonical_okx_close_sizing_hash(value),context,target,native,inventory,
        metadata,proof,expected_revision,verified.observation_hash)
    return value


def require_cleanup_preparation(service,value):
    record=service._stop_cleanup_preparations.get(id(value));now=service.clock()
    if (type(value) is not _StopCleanupPreparation or record is None or record[0] is not value or
            record[1]!=canonical_okx_close_sizing_hash(value) or not value.created_at<=now<value.created_at+timedelta(seconds=5)):
        raise RuntimeAdmissionError('CLEANUP_CURRENT_ORIGINAL_PREPARATION_REQUIRED')
    _,_,before,target,native,inventory,metadata,proof,revision,verified_hash=record
    current,verified=_source(service,value.stop_operation_id,target,native,inventory,metadata,proof,revision)
    if replace(current,generation=before.generation)!=before or verified.observation_hash!=verified_hash:
        raise RuntimeAdmissionError('CLEANUP_ORIGINAL_CANONICAL_SUBJECT_CHANGED')
    service.dispatch.require_claim_inventory_generation(current.generation)
    return record,current


def require_cleanup_final_freshness(service,value,*,permit):
    """Local issuer/window fence after semantic/SQLite work, before cancel."""
    _fixture(service)
    record=service._stop_cleanup_preparations.get(id(value))
    if (type(value) is not _StopCleanupPreparation or record is None or record[0] is not value or
            record[1]!=canonical_okx_close_sizing_hash(value)):
        raise RuntimeAdmissionError('CLEANUP_CURRENT_ORIGINAL_PREPARATION_REQUIRED')
    _,_,context,target,native,inventory,metadata,proof,_,_=record
    if context.lease!=service.lease or context.provider is not service.provider:
        raise RuntimeAdmissionError('CLEANUP_CURRENT_ORIGINAL_READ_ISSUER_REQUIRED')
    for item,pool in ((target,service._cleanup_stop_reads),(native,service._position_reads),
            (inventory,service._algo_inventories)):
        issued=pool.get(id(item))
        if (issued is None or issued[0] is not item or issued[1]!=canonical_okx_close_sizing_hash(item) or
                issued[2]!=service.lease or issued[3] is not service.provider):
            raise RuntimeAdmissionError('CLEANUP_CURRENT_ORIGINAL_READ_ISSUER_REQUIRED')
    metadata_hash=canonical_okx_close_sizing_hash(metadata)
    if (native.metadata_hash!=metadata_hash or inventory.metadata_hash!=metadata_hash or
            inventory.account_hash!=proof.account_hash or target.operation_id!=value.stop_operation_id or
            target.native_algo_id!=value.native_algo_id):
        raise RuntimeAdmissionError('CLEANUP_EXACT_FINAL_READ_SUBJECT_REQUIRED')
    service.admission.require_fresh(permit,identity=service.identity,permission='MANAGE_EXISTING',execution=service.execution)
    now=service.clock()
    starts=(value.created_at,target.request_started_at,native.received_at,inventory.request_started_at,metadata.observed_at)
    if any(not start<=now<start+timedelta(seconds=5) for start in starts):
        raise RuntimeAdmissionError('CLEANUP_FINAL_READ_WINDOW_EXPIRED')
    # This also checks metadata scheduled changes, exact owner generation and
    # account/proof expiry; a proof expiry alone is not metadata currentness.
    service.translator.capabilities.require(proof,metadata,role='READ_ONLY_RECONCILIATION',now=now)


def execute_fixture_stop_cleanup(service,value,*,expected_revision):
    from application.trading.service import TradingOutcome
    _fixture(service);service._guard(expected_revision,'MANAGE_EXISTING')
    record,current=require_cleanup_preparation(service,value)
    if expected_revision!=record[8]:raise RuntimeAdmissionError('CLEANUP_ORIGINAL_RUNTIME_REVISION_REQUIRED')
    _,_,_,target,native,inventory,metadata,proof,_,verified_hash=record
    source=dict(profile='fixture-stop-cleanup-read-evidence-v0.2',flat_native=observation_material(native),
        inventory=inventory_material(inventory),targeted_stop=dict(operation_id=target.operation_id,native_algo_id=target.native_algo_id,
            row=json.loads(target.row_json),source_hash=target.source_hash,request_started_at=target.request_started_at.isoformat(),received_at=target.received_at.isoformat()),
        canonical_graph_hash=canonical_okx_close_sizing_hash(current.recovered),verified_stop_publication_hash=verified_hash,
        metadata_hash=canonical_okx_close_sizing_hash(metadata),prepared_at=value.created_at.isoformat())
    claimed=service.dispatch.claim_stop_cleanup(service.run_id,value.stop_operation_id,value.close_operation_id,value.native_algo_id,
        value.flat_publication_hash,source,lease=service.lease,now=service.clock(),claim_inventory_generation=current.generation)
    outcome=TradingOutcome(value.stop_operation_id,'CLEANUP_READBACK_REQUIRED','CANCEL_CLAIM_IS_NOT_TERMINAL_EVIDENCE')
    if not claimed:return outcome
    guard=service._guard(expected_revision,'MANAGE_EXISTING',cleanup=value)
    try:service.provider.request('POST','/api/v5/trade/cancel-algos',guard=guard,
        body=[dict(instId='BTC-USDT-SWAP',algoId=value.native_algo_id)])
    except ProductProviderError:pass
    return outcome
