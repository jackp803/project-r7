"""E6 position observation/outbox extension, on the existing dispatch connection.

Native audit facts stay here. Canonical publication uses only actual E5 outputs;
persisted facts or receipts never grant provider or financial authority.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from brokers.okx_product_position import ProductPositionObservation
from brokers.okx_product_inventory import ProductAlgoInventoryObservation
import json
from brokers.okx_product_state import restore_product_readback
from registry.product_assessment import digest
from storage._runtime_validation import validate_raw_position,broker_fact_hash
from storage.runtime import _reject_provider_native_fields
from position.lifecycle_projection import validate_position_lifecycle_projection
from position.lifecycle_execution_binding import validate_position_lifecycle_execution_evidence_binding
from position.entry_observation import product_entry_position_id


def _ports():
    from storage.product_dispatch import ProductDispatchError,_json,_read,_stamp
    return ProductDispatchError,_json,_read,_stamp


@dataclass(frozen=True)
class ProductProtectionObservation:
    position:ProductPositionObservation
    inventory:ProductAlgoInventoryObservation
    source_lifecycle_projection_id:str
    fp04_evidence_json:str
    fp11_evidence_json:str
    reason_code:str

    @property
    def received_at(self):return self.inventory.received_at


def inventory_material(value):
    Error,_,_,stamp=_ports()
    if type(value) is not ProductAlgoInventoryObservation:raise Error('POSITION_ACTUAL_NATIVE_INVENTORY_REQUIRED')
    return dict(profile=value.profile,algo_types=list(value.algo_types),coverage=value.coverage,
        request_started_at=stamp(value.request_started_at),received_at=stamp(value.received_at),
        request_count=value.request_count,account_hash=value.account_hash,metadata_hash=value.metadata_hash,
        objects=[dict(provider_algo_id=item.provider_algo_id,algo_type=item.algo_type,
            provider_created_at=stamp(item.provider_created_at),
            provider_updated_at=None if item.provider_updated_at is None else stamp(item.provider_updated_at),
            row_json=item.row_json,source_hash=item.source_hash) for item in value.objects])


def observation_material(value):
    Error,_,_,stamp=_ports()
    if type(value) is ProductProtectionObservation:
        from position.external_close_policy import validate_external_provider_ownership_evidence
        from execution.protection_registry_evidence import validate_protection_registry_multiplicity_evidence
        dependencies=json.loads(value.fp04_evidence_json);registry=json.loads(value.fp11_evidence_json)
        if not isinstance(dependencies,list):raise Error('POSITION_EXACT_PROTECTION_OWNER_EVIDENCE_REQUIRED')
        for item in dependencies:validate_external_provider_ownership_evidence(item)
        validate_protection_registry_multiplicity_evidence(registry)
        return dict(profile='product-protection-observation-v0.2',position=observation_material(value.position),
            inventory=inventory_material(value.inventory),source_lifecycle_projection_id=value.source_lifecycle_projection_id,
            fp04_evidence=dependencies,fp11_evidence=registry,reason_code=value.reason_code)
    if type(value) is not ProductPositionObservation:raise Error('POSITION_ACTUAL_NATIVE_READBACK_REQUIRED')
    return dict(profile=value.profile,provider_position_id=value.provider_position_id,
        provider_contract_quantity=str(value.provider_contract_quantity),canonical_net_quantity=str(value.canonical_net_quantity),
        average_entry_price=None if value.average_entry_price is None else str(value.average_entry_price),
        provider_updated_at=stamp(value.provider_updated_at),request_started_at=stamp(value.request_started_at),
        received_at=stamp(value.received_at),metadata_hash=value.metadata_hash)


@dataclass(frozen=True)
class ProductPositionPublication:
    run_id:str
    operation_id:str
    observed_at:str
    observation_json:str
    observation_hash:str
    effects_json:str
    effects_hash:str

    @property
    def effects(self):return _ports()[2](self.effects_json,self.effects_hash)


def _effects(value,request,observation):
    Error,encode,_,stamp=_ports()
    managing=type(observation) is ProductProtectionObservation
    native=observation.position if managing else observation
    expected=product_entry_position_id(request.trade_plan_id)
    if (not isinstance(value,list) or not 3<=len(value)<=101 or len(value)%2!=1 or
        any(not isinstance(item,dict) or set(item)!={'kind','payload'} or not isinstance(item['payload'],dict) for item in value)):
        raise Error('POSITION_EXACT_E5_PUBLICATION_REQUIRED')
    raw=value[0]['payload']
    if value[0]['kind']!='RAW_POSITION':raise Error('POSITION_EXACT_E5_PUBLICATION_REQUIRED')
    validate_raw_position(raw)
    quantity=Decimal(raw['actual_quantity'])
    observed=stamp(datetime.fromisoformat(raw['broker_state_observed_at'].replace('Z','+00:00')))
    expected_side=(('SHORT' if request.side.value=='BUY' else 'LONG') if managing else
                   ('LONG' if request.side.value=='BUY' else 'SHORT'))
    if raw['position_id']!=expected or raw['symbol']!=request.symbol or raw['side']!=expected_side:
        raise Error('POSITION_EXACT_ENTRY_OBSERVATION_REQUIRED')
    if (quantity!=abs(native.canonical_net_quantity) or quantity<=0 or not managing and quantity>request.quantity or
        native.canonical_net_quantity!=(quantity if raw['side']=='LONG' else -quantity) or
        observed!=stamp(native.received_at) or Decimal(raw['average_entry_price'])!=native.average_entry_price):
        raise Error('POSITION_EXACT_ENTRY_OBSERVATION_REQUIRED')
    for index in range(1,len(value),2):
        projection,binding=value[index],value[index+1]
        if projection['kind']!='POSITION_PROJECTION' or binding['kind']!='LIFECYCLE_EXECUTION_BINDING':
            raise Error('POSITION_EXACT_E5_PUBLICATION_REQUIRED')
        validate_position_lifecycle_projection(projection['payload'])
        validate_position_lifecycle_execution_evidence_binding(binding['payload'],projection['payload'])
        if broker_fact_hash(projection['payload'])!=broker_fact_hash(raw):
            raise Error('POSITION_EXACT_ENTRY_OBSERVATION_REQUIRED')
        if managing and (projection['payload']['previous_lifecycle_projection_id']!=observation.source_lifecycle_projection_id or
                         projection['payload']['lifecycle_state']=='CLOSED'):
            raise Error('POSITION_EXACT_PROTECTION_PROJECTION_REQUIRED')
    for item in value:_reject_provider_native_fields(item['payload'])
    return encode(value)


def _batch(row):
    _,_,read,_=_ports()
    read(row['observation_json'],row['observation_hash']);read(row['effects_json'],row['effects_hash'])
    return ProductPositionPublication(*(row[name] for name in ('run_id','operation_id','observed_at',
        'observation_json','observation_hash','effects_json','effects_hash')))


def position_publication(journal,run_id,operation_id,received_at):
    stamp=_ports()[3];journal._run(run_id)
    row=journal._db.execute('SELECT * FROM product_position_outbox WHERE run_id=? AND operation_id=? AND observed_at=?',
        (run_id,operation_id,stamp(received_at))).fetchone()
    return None if row is None else _batch(row)


def latest_position_publication(journal,run_id,operation_id):
    journal._run(run_id)
    row=journal._db.execute('SELECT * FROM product_position_outbox WHERE run_id=? AND operation_id=? ORDER BY observed_at DESC LIMIT 1',
        (run_id,operation_id)).fetchone()
    return None if row is None else _batch(row)


def observe_position(journal,run_id,operation_id,observation,effects,*,lease,now,claim_inventory_generation=None):
    Error,encode,_,stamp=_ports()
    if type(observation) not in (ProductPositionObservation,ProductProtectionObservation):raise Error('POSITION_ACTUAL_NATIVE_READBACK_REQUIRED')
    at=stamp(now);observed=stamp(observation.received_at)
    material=observation_material(observation);raw=encode(material)
    with journal._write():
        if type(observation) is ProductProtectionObservation:
            # BEGIN IMMEDIATE prevents another claim append between this final
            # fence and the immutable protection outbox commit.
            journal.require_claim_inventory_generation(claim_inventory_generation)
        journal._run(run_id);journal._require_lease(run_id,lease,at)
        operation=journal.operation(run_id,operation_id)
        if operation is None or operation.recovery_disposition!='READBACK_REQUIRED':raise Error('POSITION_PRIOR_DISPATCH_CLAIM_REQUIRED')
        prepared=restore_product_readback(operation.request)
        role='PROTECTION_STOP' if type(observation) is ProductProtectionObservation else 'ENTRY'
        if prepared.role!=role or observed>at:raise Error('POSITION_ORIGINAL_ENTRY_REQUIRED')
        claim=journal._db.execute('SELECT dispatched_at FROM product_dispatch_claims WHERE run_id=? AND operation_id=?',
            (run_id,operation_id)).fetchone()
        if observed<claim['dispatched_at']:raise Error('POSITION_READBACK_BEFORE_DISPATCH')
        effects_raw=_effects(effects,prepared.canonical_request,observation)
        existing=position_publication(journal,run_id,operation_id,observation.received_at)
        if existing is not None:
            if (existing.observation_json,existing.effects_json)!=(raw,effects_raw):raise Error('POSITION_EQUAL_TIME_OBSERVATION_CONFLICT')
        else:
            journal._db.execute('INSERT INTO product_position_outbox VALUES(?,?,?,?,?,?,?,?)',
                (run_id,operation_id,observed,raw,digest(raw),effects_raw,digest(effects_raw),lease.generation))
    return position_publication(journal,run_id,operation_id,observation.received_at)


def pending_position_publications(journal,run_id):
    journal._run(run_id)
    return tuple(_batch(row) for row in journal._db.execute('SELECT o.* FROM product_position_outbox o '
        'LEFT JOIN product_position_publications p USING(run_id,operation_id,observed_at) '
        'WHERE o.run_id=? AND p.operation_id IS NULL ORDER BY o.observed_at,o.operation_id LIMIT 1000',(run_id,)).fetchall())


def mark_position_publication(journal,batch,*,lease,now):
    Error,_,_,stamp=_ports();at=stamp(now)
    if type(batch) is not ProductPositionPublication:raise Error('POSITION_EXACT_PUBLICATION_RECEIPT_REQUIRED')
    with journal._write():
        journal._run(batch.run_id);journal._require_lease(batch.run_id,lease,at)
        stored=position_publication(journal,batch.run_id,batch.operation_id,datetime.fromisoformat(batch.observed_at.replace('Z','+00:00')))
        if stored!=batch or at<batch.observed_at:raise Error('POSITION_EXACT_PUBLICATION_RECEIPT_REQUIRED')
        journal._db.execute('INSERT OR IGNORE INTO product_position_publications VALUES(?,?,?,?,?,?)',
            (batch.run_id,batch.operation_id,batch.observed_at,batch.effects_hash,lease.generation,at))
