"""E6 immutable funding publication, with no source truth or provider capability."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re

from brokers.okx_product_state import restore_product_readback
from execution.ledger_funding import FIXTURE_SOURCE,FIXTURE_SOURCE_VERSION,FIXTURE_WIRE_PROFILE
from storage._runtime_validation import validate_funding_evidence
from storage.product_position import latest_position_publication


def _ports():
    from storage.product_dispatch import ProductDispatchError,_json,_read,_stamp
    return ProductDispatchError,_json,_read,_stamp


@dataclass(frozen=True)
class ProductFundingObservation:
    entry_operation_id:str
    close_publication_hash:str
    source_material_json:str
    funding_evidence_json:str
    received_at:datetime


@dataclass(frozen=True)
class ProductFundingPublication:
    run_id:str
    operation_id:str
    observed_at:str
    funding_evidence_id:str
    observation_json:str
    observation_hash:str
    effects_json:str
    effects_hash:str

    @property
    def effects(self):
        Error,encode,read,_=_ports()
        if (not isinstance(self.observation_json,str) or len(self.observation_json)>1048576 or
                not isinstance(self.effects_json,str) or len(self.effects_json)>65536):
            raise Error('FUNDING_BOUNDED_PUBLICATION_REQUIRED')
        value=_ports()[2](self.effects_json,self.effects_hash)
        if (type(value) is not list or len(value)!=1 or type(value[0]) is not dict or
                set(value[0])!={'kind','payload'} or value[0]['kind']!='FUNDING_EVIDENCE'):
            raise _ports()[0]('FUNDING_EXACT_PUBLICATION_REQUIRED')
        validate_funding_evidence(value[0]['payload'])
        if value[0]['payload']['funding_evidence_id']!=self.funding_evidence_id:
            raise _ports()[0]('FUNDING_EXACT_PUBLICATION_REQUIRED')
        material=read(self.observation_json,self.observation_hash);evidence=value[0]['payload']
        if (type(material) is not dict or set(material)!={'profile','entry_operation_id','close_publication_hash','received_at','source_material'} or
                material['profile']!='product-funding-ledger-observation-v0.2' or
                material['received_at']!=self.observed_at or not isinstance(material['close_publication_hash'],str) or
                not re.fullmatch('sha256:[0-9a-f]{64}',material['close_publication_hash'])):
            raise Error('FUNDING_EXACT_OBSERVATION_REQUIRED')
        source=material['source_material']
        if (type(source) is not dict or source.get('profile')!=FIXTURE_WIRE_PROFILE or
                (source.get('source'),source.get('source_version'))!=(FIXTURE_SOURCE,FIXTURE_SOURCE_VERSION) or
                (evidence['source'],evidence['source_version'],evidence['source_kind'])!=(FIXTURE_SOURCE,FIXTURE_SOURCE_VERSION,'BROKER_LEDGER') or
                hashlib.sha256(encode(source).encode()).hexdigest()!=evidence['source_material_hash'] or
                any(source.get(key)!=evidence[key] for key in ('trade_plan_id','position_id','symbol','interval_start','interval_end')) or
                source.get('complete_through')!=evidence['source_complete_through'] or
                type(source.get('records')) is not list or len(source['records'])!=evidence['source_record_count']):
            raise Error('FUNDING_EXACT_SOURCE_MATERIAL_REQUIRED')
        return value


def _batch(row):
    result=ProductFundingPublication(*(row[k] for k in ('run_id','operation_id','observed_at','funding_evidence_id',
        'observation_json','observation_hash','effects_json','effects_hash')))
    result.effects
    return result


def _require_original(journal,run_id,operation_id,entry_operation_id,flat_hash,evidence,observed,source):
    Error,_,_,_=_ports();run=journal._run(run_id)
    if journal._db.execute('SELECT namespace FROM product_dispatch_namespace WHERE singleton=1').fetchone()[0]!='FIXTURE':
        raise Error('FUNDING_FIXTURE_SOURCE_NAMESPACE_REQUIRED')
    operation=journal.operation(run_id,operation_id);entry=journal.operation(run_id,entry_operation_id)
    if (operation is None or entry is None or operation.recovery_disposition!='READBACK_REQUIRED' or
            entry.recovery_disposition!='READBACK_REQUIRED'):
        raise Error('FUNDING_ORIGINAL_CLAIM_REQUIRED')
    prepared=restore_product_readback(operation.request);original=restore_product_readback(entry.request)
    flat=latest_position_publication(journal,run_id,operation_id)
    entry_publication=latest_position_publication(journal,run_id,entry_operation_id)
    if flat is None or entry_publication is None:raise Error('FUNDING_ORIGINAL_NATIVE_FLAT_REQUIRED')
    from storage.product_dispatch import _read
    native=_read(flat.observation_json,flat.observation_hash)
    entry_native=_read(entry_publication.observation_json,entry_publication.observation_hash)
    if (prepared.role not in ('POSITION_EXIT','EMERGENCY_EXIT') or original.role!='ENTRY' or
            original.canonical_request.trade_plan_id!=prepared.canonical_request.trade_plan_id or
            native.get('profile')!='product-close-native-observation-v0.2' or
            entry_native.get('profile')!='okx-product-position-readback-v0.2' or
            native['entry_operation_id']!=entry_operation_id or
            native['position']['provider_position_id']!=entry_native['provider_position_id'] or
            Decimal(native['position']['canonical_net_quantity'])!=0 or
            flat.observation_hash!=flat_hash or flat.observed_at>observed):
        raise Error('FUNDING_ORIGINAL_NATIVE_FLAT_REQUIRED')
    position=flat.effects[-2]['payload']
    if (any(evidence[key]!=position[key] for key in ('position_id','symbol')) or
            evidence['trade_plan_id']!=prepared.canonical_request.trade_plan_id or
            evidence['position_id']!=prepared.canonical_request.position_id or
            evidence['interval_start']!=position['opened_at'] or evidence['interval_end']!=position['broker_state_observed_at'] or
            position['lifecycle_state']!='EXIT_REQUESTED' or Decimal(position['actual_quantity'])!=0):
        raise Error('FUNDING_EXACT_CANONICAL_FLAT_REQUIRED')
    from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
    from registry.product_assessment import canonical
    scope=dict(trade_plan_id=evidence['trade_plan_id'],position_id=evidence['position_id'],symbol=evidence['symbol'],
        account_hash=canonical_okx_close_sizing_hash(dict(provider_ref=run['provider_ref'],account_ref=run['account_ref'])),
        provider_ref=run['provider_ref'],native_position_id=entry_native['provider_position_id'])
    if source.get('scope_commitment')!=hashlib.sha256(canonical(scope).encode()).hexdigest():
        raise Error('FUNDING_ORIGINAL_SOURCE_SCOPE_REQUIRED')


def _require_batch_original(journal,batch):
    evidence=batch.effects[0]['payload'];material=_ports()[2](batch.observation_json,batch.observation_hash)
    _require_original(journal,batch.run_id,batch.operation_id,material['entry_operation_id'],material['close_publication_hash'],
        evidence,batch.observed_at,material['source_material'])


def funding_publication(journal,run_id,operation_id,received_at):
    stamp=_ports()[3];journal._run(run_id)
    row=journal._db.execute('SELECT * FROM product_dispatch_funding_outbox WHERE run_id=? AND operation_id=? AND observed_at=?',
        (run_id,operation_id,stamp(received_at))).fetchone()
    if row is None:return None
    result=_batch(row);_require_batch_original(journal,result);return result


def observe_funding(journal,run_id,operation_id,observation,*,lease,now,claim_inventory_generation):
    Error,encode,_,stamp=_ports()
    if type(observation) is not ProductFundingObservation:raise Error('FUNDING_ACTUAL_SOURCE_OBSERVATION_REQUIRED')
    if (not isinstance(observation.source_material_json,str) or len(observation.source_material_json)>1048576 or
            not isinstance(observation.funding_evidence_json,str) or len(observation.funding_evidence_json)>65536):
        raise Error('FUNDING_BOUNDED_SOURCE_OBSERVATION_REQUIRED')
    source=json.loads(observation.source_material_json);evidence=json.loads(observation.funding_evidence_json)
    validate_funding_evidence(evidence)
    if (type(source) is not dict or source.get('profile')!=FIXTURE_WIRE_PROFILE or
            (evidence['source'],evidence['source_version'],evidence['source_kind'])!=(FIXTURE_SOURCE,FIXTURE_SOURCE_VERSION,'BROKER_LEDGER') or
            hashlib.sha256(observation.source_material_json.encode()).hexdigest()!=evidence['source_material_hash']):
        raise Error('FUNDING_EXACT_SOURCE_MATERIAL_REQUIRED')
    observed,at=stamp(observation.received_at),stamp(now)
    material=dict(profile='product-funding-ledger-observation-v0.2',entry_operation_id=observation.entry_operation_id,
        close_publication_hash=observation.close_publication_hash,received_at=observed,source_material=source)
    raw=encode(material);effects=encode([dict(kind='FUNDING_EVIDENCE',payload=evidence)])
    from registry.product_assessment import digest
    with journal._write():
        journal.require_claim_inventory_generation(claim_inventory_generation)
        journal._run(run_id);journal._require_lease(run_id,lease,at)
        if journal._db.execute('SELECT namespace FROM product_dispatch_namespace WHERE singleton=1').fetchone()[0]!='FIXTURE':
            raise Error('FUNDING_FIXTURE_SOURCE_NAMESPACE_REQUIRED')
        if observed>at:raise Error('FUNDING_ORIGINAL_CLAIM_REQUIRED')
        _require_original(journal,run_id,operation_id,observation.entry_operation_id,observation.close_publication_hash,evidence,observed,source)
        existing=funding_publication(journal,run_id,operation_id,observation.received_at)
        if existing is not None:
            if (existing.observation_json,existing.effects_json)!=(raw,effects):raise Error('FUNDING_EQUAL_TIME_OBSERVATION_CONFLICT')
        else:
            journal._db.execute('INSERT INTO product_dispatch_funding_outbox VALUES(?,?,?,?,?,?,?,?,?)',
                (run_id,operation_id,observed,evidence['funding_evidence_id'],raw,digest(raw),effects,digest(effects),lease.generation))
    return funding_publication(journal,run_id,operation_id,observation.received_at)


def pending_funding_publications(journal,run_id):
    journal._run(run_id)
    batches=tuple(_batch(row) for row in journal._db.execute('SELECT o.* FROM product_dispatch_funding_outbox o '
        'LEFT JOIN product_dispatch_funding_publications p USING(run_id,operation_id,observed_at) '
        'WHERE o.run_id=? AND p.operation_id IS NULL ORDER BY o.observed_at,o.operation_id LIMIT 1000',(run_id,)).fetchall())
    for batch in batches:_require_batch_original(journal,batch)
    return batches


def mark_funding_publication(journal,batch,*,lease,now):
    Error,_,_,stamp=_ports();at=stamp(now)
    if type(batch) is not ProductFundingPublication:raise Error('FUNDING_EXACT_PUBLICATION_RECEIPT_REQUIRED')
    with journal._write():
        journal._run(batch.run_id);journal._require_lease(batch.run_id,lease,at)
        stored=funding_publication(journal,batch.run_id,batch.operation_id,datetime.fromisoformat(batch.observed_at.replace('Z','+00:00')))
        if stored!=batch or at<batch.observed_at:raise Error('FUNDING_EXACT_PUBLICATION_RECEIPT_REQUIRED')
        batch.effects
        existing=journal._db.execute('SELECT * FROM product_dispatch_funding_publications WHERE run_id=? AND operation_id=? AND observed_at=?',
            (batch.run_id,batch.operation_id,batch.observed_at)).fetchone()
        if existing is not None:
            if existing['effects_hash']!=batch.effects_hash or existing['published_at']<batch.observed_at:
                raise Error('FUNDING_EXACT_PUBLICATION_RECEIPT_REQUIRED')
            return
        journal._db.execute('INSERT INTO product_dispatch_funding_publications VALUES(?,?,?,?,?,?)',
            (batch.run_id,batch.operation_id,batch.observed_at,batch.effects_hash,lease.generation,at))
