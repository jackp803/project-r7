"""Issued exact canceled-stop read, restricted to original FIXTURE cleanup.

These facts never project a Position, create a TradeResult, or authorize an
effect. The existing active inventory parser and funding READY guard stay intact.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta
from decimal import Decimal
import json

from application.trading.admission import RuntimeAdmissionError
from application.trading.close_owner import original_entry
from application.trading.funding_owner import _fixture
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_state import restore_product_readback
from brokers.okx_terminal_stop import ProductTerminalStopObservation,parse_product_terminal_stop
from storage.product_dispatch import _read


def _at(value):return datetime.fromisoformat(value.replace('Z','+00:00'))


@dataclass(frozen=True)
class _TerminalSource:
    stop_operation_id:str
    close_operation_id:str
    native_algo_id:str
    provider_created_at:datetime
    flat_broker_at:datetime
    generation:object
    source_hash:str


def _source(service,operation_id,revision):
    _fixture(service);service._guard(revision,'MANAGE_EXISTING')
    service.recover_publications()
    generation=service.dispatch.claim_inventory_generation()
    operation=service.dispatch.operation(service.run_id,operation_id)
    claim=service.dispatch.stop_cleanup_claim(service.run_id,operation_id)
    if operation is None or claim is None or operation.recovery_disposition!='READBACK_REQUIRED':
        raise RuntimeAdmissionError('TERMINAL_ORIGINAL_CLEANUP_CLAIM_REQUIRED')
    prepared=restore_product_readback(operation.request);request=prepared.canonical_request
    close=service.dispatch.operation(service.run_id,claim.close_operation_id)
    if prepared.role!='PROTECTION_STOP' or close is None or close.recovery_disposition!='READBACK_REQUIRED':
        raise RuntimeAdmissionError('TERMINAL_ORIGINAL_STOP_AND_CLOSE_REQUIRED')
    exit_prepared=restore_product_readback(close.request)
    if (exit_prepared.role not in ('POSITION_EXIT','EMERGENCY_EXIT') or
            (exit_prepared.canonical_request.position_id,exit_prepared.canonical_request.trade_plan_id)!=
            (request.position_id,request.trade_plan_id)):
        raise RuntimeAdmissionError('TERMINAL_ORIGINAL_STOP_AND_CLOSE_REQUIRED')
    stops=tuple(service.dispatch.iter_claimed_initial_protections_for_position(service.run_id,request.position_id))
    closes=tuple(service.dispatch.iter_claimed_closes_for_position(service.run_id,request.position_id))
    if ([(x.run_id,x.operation_id) for x in stops]!=[(service.run_id,operation_id)] or
            [(x.run_id,x.operation_id) for x in closes]!=[(service.run_id,claim.close_operation_id)]):
        raise RuntimeAdmissionError('TERMINAL_SINGLE_ORIGINAL_STOP_AND_CLOSE_REQUIRED')
    entry,entry_prepared,entry_publication,native=original_entry(service,request.trade_plan_id)
    recovered=service.canonical.recover(trade_plan_id=request.trade_plan_id,position_id=request.position_id)
    if not (recovered.status=='READY' and not recovered.reason_codes or
            recovered.status=='REINTERPRETATION_REQUIRED' and
            recovered.reason_codes==('E5_EXECUTION_REINTERPRETATION_REQUIRED',)):
        raise RuntimeAdmissionError('TERMINAL_ORIGINAL_CANONICAL_GRAPH_REQUIRED')
    current=[x for x in recovered.current_order_results if x.payload['order_request_id']==operation_id]
    requests=[x for x in recovered.order_requests if x.canonical_id==operation_id]
    observation={} if operation.observation_json is None else json.loads(operation.observation_json)
    if (len(current)!=1 or current[0].payload['order_status']!='CANCELED' or
            Decimal(current[0].payload['filled_quantity'])!=0 or current[0].payload['broker_order_id']!=claim.native_algo_id or
            observation.get('provider_id')!=claim.native_algo_id or len(requests)!=1 or
            requests[0].payload!=operation.request['canonical_request'] or
            any(x.payload['client_order_id']==request.client_order_id for x in recovered.fills)):
        raise RuntimeAdmissionError('TERMINAL_ACTUAL_CANONICAL_UNUSED_STOP_CANCELED_REQUIRED')
    verified=service.dispatch.latest_position_publication(service.run_id,operation_id)
    flat=service.dispatch.latest_position_publication(service.run_id,claim.close_operation_id)
    if verified is None or flat is None:raise RuntimeAdmissionError('TERMINAL_ORIGINAL_NATIVE_PUBLICATIONS_REQUIRED')
    protection=_read(verified.observation_json,verified.observation_hash)
    zero=_read(flat.observation_json,flat.observation_hash)
    identity=json.loads(claim.identity_json)
    position=None if recovered.current_position_projection is None else recovered.current_position_projection.payload
    if (protection.get('profile')!='product-protection-observation-v0.2' or
            zero.get('profile')!='product-close-native-observation-v0.2' or
            identity.get('flat_publication_hash')!=flat.observation_hash or
            zero['entry_operation_id']!=entry.operation_id or
            zero['position']['provider_position_id']!=native['provider_position_id'] or
            Decimal(zero['position']['canonical_net_quantity'])!=0 or
            position!=flat.effects[-2]['payload'] or position['lifecycle_state']!='EXIT_REQUESTED' or
            Decimal(position['actual_quantity'])!=0):
        raise RuntimeAdmissionError('TERMINAL_ORIGINAL_NATIVE_FLAT_REQUIRED')
    objects=[x for x in protection['inventory']['objects'] if x['provider_algo_id']==claim.native_algo_id]
    subject=service.canonical.current_execution_subject(service.identity,request.trade_plan_id)
    if (len(objects)!=1 or verified.effects[-2]['payload']['lifecycle_state'] not in ('OPEN_PROTECTED','PROFIT_PROTECTED') or
            any(x.source_plan_hash!=canonical_okx_close_sizing_hash(subject.approved_trade_plan.payload)
                for x in (prepared,exit_prepared,entry_prepared))):
        raise RuntimeAdmissionError('TERMINAL_ORIGINAL_VERIFIED_STOP_REQUIRED')
    material=dict(stop_request=operation.request_json,stop_observation=operation.observation_json,
        close_request=close.request_json,cleanup_identity=claim.identity_json,cleanup_source=claim.source_json,
        entry_request=entry.request_json,entry_publication=entry_publication.observation_hash,
        flat_publication=flat.observation_hash,verified_publication=verified.observation_hash,
        recovered=recovered,risk=subject.risk_decision,plan=subject.approved_trade_plan)
    service.dispatch.require_claim_inventory_generation(generation)
    service.canonical.require_current_execution_subject(subject)
    return _TerminalSource(operation_id,claim.close_operation_id,claim.native_algo_id,
        _at(objects[0]['provider_created_at']),_at(position['broker_state_observed_at']),generation,
        canonical_okx_close_sizing_hash(material)),prepared


@dataclass(frozen=True)
class ProductTerminalStopRead:
    operation_id:str
    close_operation_id:str
    request_started_at:datetime
    observation:ProductTerminalStopObservation

    @property
    def status(self):return self.observation.status


def read_fixture_terminal_stop(service,operation_id,*,expected_revision):
    before,prepared=_source(service,operation_id,expected_revision)
    lease,provider=service.lease,service.provider;started=service.clock()
    response=service._read('/api/v5/trade/order-algo',dict(algoId=before.native_algo_id),expected_revision)
    observation=parse_product_terminal_stop(response,prepared,received_at=service.clock(),expected_provider_id=before.native_algo_id)
    after,_=_source(service,operation_id,expected_revision)
    now=service.clock()
    if (before!=after or service.lease!=lease or service.provider is not provider or
            not started<=observation.received_at<=now<started+timedelta(seconds=5) or
            observation.provider_created_at!=before.provider_created_at or observation.provider_updated_at<before.flat_broker_at):
        raise RuntimeAdmissionError('TERMINAL_CURRENT_ORIGINAL_TARGET_READ_REQUIRED')
    value=ProductTerminalStopRead(operation_id,before.close_operation_id,started,observation)
    service._terminal_stop_reads={key:record for key,record in service._terminal_stop_reads.items()
        if record[0].request_started_at+timedelta(seconds=5)>now}
    if len(service._terminal_stop_reads)>=128:raise RuntimeAdmissionError('TERMINAL_READ_ISSUANCE_LIMIT')
    service._terminal_stop_reads[id(value)]=(value,canonical_okx_close_sizing_hash(value),lease,provider,after,expected_revision)
    return value


def _issued(service,value,operation_id):
    _fixture(service);record=service._terminal_stop_reads.get(id(value));now=service.clock()
    if (type(value) is not ProductTerminalStopRead or record is None or record[0] is not value or
            record[1]!=canonical_okx_close_sizing_hash(value) or record[2]!=service.lease or record[3] is not service.provider or
            value.operation_id!=operation_id or not value.request_started_at<=now<value.request_started_at+timedelta(seconds=5)):
        raise RuntimeAdmissionError('TERMINAL_CURRENT_ORIGINAL_ISSUED_READ_REQUIRED')
    return record


def require_terminal_stop_read(service,value,operation_id):
    record=_issued(service,value,operation_id)
    after,_=_source(service,operation_id,record[5])
    if after!=record[4]:
        raise RuntimeAdmissionError('TERMINAL_ORIGINAL_SOURCE_CHANGED_OR_EXPIRED')
    service.dispatch.require_claim_inventory_generation(after.generation)
    service.dispatch.require_process(record[2],now=service.clock())
    # Semantic scans must not consume an issuer/context which changed during
    # that scan. This final local fence never renews the original read window.
    if _issued(service,value,operation_id) is not record:
        raise RuntimeAdmissionError('TERMINAL_ORIGINAL_ISSUANCE_RECORD_CHANGED')
