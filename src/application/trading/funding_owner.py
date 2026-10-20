"""Actual FIXTURE owner composition for E4 allocated-ledger funding evidence.

No HTTP-supplied source, final Position, complete flag or provider driver.
Actual production ledger mapping remains unsupported and is denied here.
"""
from dataclasses import dataclass,replace
from datetime import datetime,timedelta
from decimal import Decimal
import json

from application.trading.admission import RuntimeAdmissionError
from application.trading.close_owner import original_entry
from application.trading.provider import FakeProductProvider
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_state import restore_product_readback
from execution.ledger_funding import (FundingLedgerSubject,FixtureFundingLedgerSource,
    FIXTURE_READ_PATH,produce_broker_ledger_funding_evidence)
from registry.product_assessment import canonical
from storage.product_funding import ProductFundingObservation


def _fixture(service):
    if (service.execution!='FAKE_PROVIDER_VERIFICATION' or type(service.provider) is not FakeProductProvider or
            service.admission.namespace!='FIXTURE'):
        raise RuntimeAdmissionError('FIXTURE_ALLOCATED_FUNDING_SOURCE_ONLY')


@dataclass(frozen=True)
class _FundingContext:
    lease:object
    provider:object
    generation:object
    execution_subject:object
    recovered:object
    entry_operation:object
    close_operation:object
    flat_publication:object
    source_subject:FundingLedgerSubject


def _context(service,trade_plan_id,position_id,revision):
    _fixture(service)
    owner=service._guard(revision,'MANAGE_EXISTING').require()
    service.recover_publications()
    generation=service.dispatch.claim_inventory_generation()
    entry,entry_prepared,_,original=original_entry(service,trade_plan_id)
    recovered=service.canonical.recover(trade_plan_id=trade_plan_id,position_id=position_id)
    subject=service.canonical.current_execution_subject(service.identity,trade_plan_id)
    position=None if recovered.current_position_projection is None else recovered.current_position_projection.payload
    if (not recovered.restart_authoritative or position is None or recovered.current_lifecycle_execution_binding is None or
            recovered.trade_result is not None or position['lifecycle_state']!='EXIT_REQUESTED' or
            Decimal(position['actual_quantity'])!=0 or position['position_id']!=position_id):
        raise RuntimeAdmissionError('FUNDING_ACTUAL_CANONICAL_FLAT_REQUIRED')
    closes=tuple(service.dispatch.iter_claimed_closes_for_position(service.run_id,position_id))
    if len(closes)!=1 or closes[0].run_id!=service.run_id:
        raise RuntimeAdmissionError('FUNDING_SINGLE_ORIGINAL_CLOSE_REQUIRED')
    operation=closes[0];prepared=restore_product_readback(operation.request)
    if (prepared.role not in ('POSITION_EXIT','EMERGENCY_EXIT') or prepared.canonical_request.trade_plan_id!=trade_plan_id or
            prepared.canonical_request.position_id!=position_id or
            prepared.source_plan_hash!=canonical_okx_close_sizing_hash(subject.approved_trade_plan.payload) or
            entry_prepared.source_plan_hash!=prepared.source_plan_hash):
        raise RuntimeAdmissionError('FUNDING_ORIGINAL_CANONICAL_PLAN_REQUIRED')
    flat=service.dispatch.latest_position_publication(service.run_id,operation.operation_id)
    if flat is None:raise RuntimeAdmissionError('FUNDING_ORIGINAL_NATIVE_FLAT_REQUIRED')
    native=json.loads(flat.observation_json)
    if (native.get('profile')!='product-close-native-observation-v0.2' or native['entry_operation_id']!=entry.operation_id or
            native['position']['provider_position_id']!=original['provider_position_id'] or
            Decimal(native['position']['canonical_net_quantity'])!=0 or flat.effects[-2]['payload']!=position):
        raise RuntimeAdmissionError('FUNDING_ORIGINAL_NATIVE_FLAT_REQUIRED')
    account_scope=canonical_okx_close_sizing_hash(dict(provider_ref=owner.release.provider_ref,account_ref=owner.release.account_ref))
    source=FundingLedgerSubject(trade_plan_id,position_id,position['symbol'],account_scope,
        owner.release.provider_ref,original['provider_position_id'],position['opened_at'],position['broker_state_observed_at'])
    service.dispatch.require_claim_inventory_generation(generation)
    service.canonical.require_current_execution_subject(subject)
    return _FundingContext(service.lease,service.provider,generation,subject,recovered,entry,operation,flat,source)


@dataclass(frozen=True)
class ProductFundingRead:
    received_at:datetime
    funding_evidence_id:str
    source_material_hash:str


def read_fixture_funding_ledger(service,trade_plan_id,position_id,*,expected_revision):
    context=_context(service,trade_plan_id,position_id,expected_revision);started=service.clock();received=[]
    def reader(query):
        _fixture(service)
        if service.provider is not context.provider or service.lease!=context.lease:
            raise RuntimeAdmissionError('FUNDING_ORIGINAL_READ_ISSUER_REQUIRED')
        return service._read(FIXTURE_READ_PATH,query,expected_revision)
    def receive_clock():
        value=service.clock();received.append(value);return value
    source=FixtureFundingLedgerSource(reader)
    allocation=source.read_interval(context.source_subject,request_started_at=started,received_at=receive_clock)
    if _context(service,trade_plan_id,position_id,expected_revision)!=context:
        raise RuntimeAdmissionError('FUNDING_CANONICAL_SUBJECT_CHANGED')
    evidence=produce_broker_ledger_funding_evidence(context.execution_subject.approved_trade_plan.payload,
        context.recovered.current_position_projection.payload,allocation,source=source,calculated_at=received[0])
    value=ProductFundingRead(received[0],evidence['funding_evidence_id'],evidence['source_material_hash'])
    now=service.clock()
    service._funding_reads={key:record for key,record in service._funding_reads.items()
        if record[0].received_at+timedelta(seconds=5)>now}
    if len(service._funding_reads)>=128:raise RuntimeAdmissionError('FUNDING_READ_ISSUANCE_LIMIT')
    service._funding_reads[id(value)]=(value,canonical_okx_close_sizing_hash(value),context,source,allocation,canonical(evidence))
    return value


def publish_fixture_funding_ledger(service,value,*,expected_revision):
    _fixture(service);record=service._funding_reads.get(id(value));now=service.clock()
    if (type(value) is not ProductFundingRead or record is None or record[0] is not value or
            canonical_okx_close_sizing_hash(value)!=record[1] or not value.received_at<=now<value.received_at+timedelta(seconds=5)):
        raise RuntimeAdmissionError('FUNDING_CURRENT_ORIGINAL_SOURCE_READ_REQUIRED')
    _,_,before,source,allocation,evidence_json=record
    if service.provider is not before.provider or service.lease!=before.lease:
        raise RuntimeAdmissionError('FUNDING_CURRENT_ORIGINAL_SOURCE_READ_REQUIRED')
    source.require(allocation)
    evidence=json.loads(evidence_json)
    current=_context(service,before.source_subject.trade_plan_id,before.source_subject.position_id,expected_revision)
    saved=service.dispatch.funding_publication(service.run_id,before.close_operation.operation_id,value.received_at)
    if current.recovered.funding_evidence!=before.recovered.funding_evidence:
        # Exact replay may see its own already-published evidence. No other
        # canonical graph change is hidden by this one immutable-fact exception.
        if (before.recovered.funding_evidence or len(current.recovered.funding_evidence)!=1 or
                current.recovered.funding_evidence[0].payload_json!=evidence_json):
            raise RuntimeAdmissionError('FUNDING_CANONICAL_SUBJECT_CHANGED')
        current=replace(current,recovered=replace(current.recovered,funding_evidence=()))
    compare=replace(current,generation=before.generation) if saved is not None else current
    if compare!=before:raise RuntimeAdmissionError('FUNDING_CANONICAL_SUBJECT_CHANGED')
    observation=ProductFundingObservation(before.entry_operation.operation_id,before.flat_publication.observation_hash,
        allocation.material_json,evidence_json,value.received_at)
    if saved is not None:
        material=json.loads(saved.observation_json)
        if (saved.effects!=[dict(kind='FUNDING_EVIDENCE',payload=evidence)] or
                material.get('entry_operation_id')!=observation.entry_operation_id or
                material.get('close_publication_hash')!=observation.close_publication_hash or
                material.get('source_material')!=json.loads(observation.source_material_json)):
            raise RuntimeAdmissionError('FUNDING_ORIGINAL_PUBLICATION_REQUIRED')
        # The receipt is history, not a new publication. Re-scan/fence claims
        # above, then preserve its exact generation and original source bytes.
        service.dispatch.require_claim_inventory_generation(current.generation)
    else:
        service.dispatch.observe_funding(service.run_id,before.close_operation.operation_id,observation,lease=service.lease,
            now=service.clock(),claim_inventory_generation=before.generation)
    service.recover_publications()
    recovered=service.canonical.recover(trade_plan_id=before.source_subject.trade_plan_id,position_id=before.source_subject.position_id)
    found=[item for item in recovered.funding_evidence if item.canonical_id==evidence['funding_evidence_id']]
    if len(found)!=1:raise RuntimeAdmissionError('FUNDING_CANONICAL_PUBLICATION_INCOMPLETE')
    return found[0]
