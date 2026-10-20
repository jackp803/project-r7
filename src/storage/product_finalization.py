"""Immutable FIXTURE finalization outbox/receipt; no provider capability."""
from dataclasses import dataclass
from datetime import datetime,timedelta
from decimal import Decimal
from pathlib import Path
import hashlib,json

from brokers.okx_product_state import restore_product_readback
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_terminal_stop import parse_product_terminal_stop
from brokers.okx_product_inventory import ALGO_TYPES
from execution.models import require_utc
from registry.product_assessment import canonical,digest
from storage.product_finalization_facts import PROFILE,KINDS,build_effects,payload,fail,recover_snapshot,require_prefix


def _ports():
    from storage.product_dispatch import _json,_read,_stamp
    return _json,_read,_stamp


def _at(value):
    if type(value) is not str:fail('FINALIZATION_ORIGINAL_UTC_CLOCK_REQUIRED')
    try:
        at=datetime.fromisoformat(value.replace('Z','+00:00'))
        require_utc(at,'finalization original clock')
    except (ValueError,TypeError,AttributeError):fail('FINALIZATION_ORIGINAL_UTC_CLOCK_REQUIRED')
    return at


def require_original_clocks(source):
    """Fixed provenance relationships apply unchanged on durable replay."""
    interpreted=_at(source['interpreted_at'])
    for key in ('terminal_confirmation','native_confirmation','inventory_confirmation'):
        value=source[key]
        if not _at(value['request_started_at'])<=_at(value['received_at'])<=interpreted:
            fail('FINALIZATION_ORIGINAL_CLOCK_ORDER_REQUIRED')
    native=source['native_confirmation']
    if (_at(native['provider_updated_at'])>_at(native['received_at']) or
            _at(source['metadata_observed_at'])>interpreted):
        fail('FINALIZATION_ORIGINAL_CLOCK_ORDER_REQUIRED')


def require_distinct_journals(journal,canonical_journal):
    from storage.runtime import PaperRuntimeJournal
    if type(canonical_journal) is not PaperRuntimeJournal:fail('FINALIZATION_ACTUAL_CANONICAL_JOURNAL_REQUIRED')
    other=canonical_journal._store._connection
    if journal._db is other or journal._db.in_transaction or other.in_transaction:
        fail('FINALIZATION_DISTINCT_IDLE_JOURNALS_REQUIRED')
    paths=[]
    for connection in (journal._db,other):
        main=[row[2] for row in connection.execute('PRAGMA database_list') if row[1]=='main']
        if len(main)!=1 or not main[0]:fail('FINALIZATION_DISTINCT_LOCAL_DATABASE_FILES_REQUIRED')
        paths.append(Path(main[0]).resolve(strict=True))
    if paths[0].samefile(paths[1]):fail('FINALIZATION_DISTINCT_LOCAL_DATABASE_FILES_REQUIRED')


def claim_snapshot(journal,run_id):
    """Stable semantic history hash; PRAGMA/total_changes is only a local fence."""
    generation=journal.claim_inventory_generation();hashed=hashlib.sha256()
    for role in ('ENTRY','PROTECTION_STOP','POSITION_EXIT','EMERGENCY_EXIT'):
        for row in journal._iter_claim_inventory(run_id,role):
            material=dict(role=role,run_id=row.run_id,operation_id=row.operation_id,status=row.status,
                recovery_disposition=row.recovery_disposition,request_hash=digest(row.request_json),
                observation_hash=None if row.observation_json is None else digest(row.observation_json))
            hashed.update((canonical(material)+'\n').encode())
    journal.require_claim_inventory_generation(generation)
    return 'sha256:'+hashed.hexdigest()


def original_refs(journal,source):
    require_original_clocks(source)
    run=journal._run(source['run_id'])
    if journal._db.execute('SELECT namespace FROM product_dispatch_namespace WHERE singleton=1').fetchone()[0]!='FIXTURE':
        fail('FINALIZATION_FIXTURE_PROFILE_ONLY')
    baseline=source['baseline'];requests={x['canonical_id']:payload(x) for x in baseline['order_requests']}
    plan=payload(baseline['approved_trade_plan']);actions={x['canonical_id']:payload(x) for x in baseline['position_actions']}
    prepared=[];operations=[]
    for field,role in (('entry_operation_id','ENTRY'),('stop_operation_id','PROTECTION_STOP'),('close_operation_id',None)):
        op=journal.operation(source['run_id'],source[field])
        if op is None or op.recovery_disposition!='READBACK_REQUIRED':fail('FINALIZATION_ORIGINAL_CLAIMS_REQUIRED')
        value=restore_product_readback(op.request);request=value.canonical_request
        if ((role is not None and value.role!=role) or (role is None and value.role not in ('POSITION_EXIT','EMERGENCY_EXIT')) or
                op.request['canonical_request']!=requests.get(op.operation_id) or
                value.source_plan_hash!=canonical_okx_close_sizing_hash(plan)):
            fail('FINALIZATION_ORIGINAL_REQUEST_AND_PLAN_REQUIRED')
        if role!='ENTRY':
            action=actions.get(request.position_action_id)
            if (request.position_id!=source['position_id'] or action is None or
                    value.source_action_hash!=canonical_okx_close_sizing_hash(action) or
                    not any(value.source_position_hash==canonical_okx_close_sizing_hash(payload(row)) for row in baseline['lifecycle_history'])):
                fail('FINALIZATION_ORIGINAL_E5_ACTION_AND_POSITION_REQUIRED')
        prepared.append(value);operations.append(dict(operation_id=op.operation_id,request_hash=digest(op.request_json),
            observation_hash=None if op.observation_json is None else digest(op.observation_json),status=op.status))
    claim=journal.stop_cleanup_claim(source['run_id'],source['stop_operation_id'])
    flat=journal.latest_position_publication(source['run_id'],source['close_operation_id'])
    verified=journal.latest_position_publication(source['run_id'],source['stop_operation_id'])
    entry=journal.latest_position_publication(source['run_id'],source['entry_operation_id'])
    if claim is None or flat is None or verified is None or entry is None:fail('FINALIZATION_ORIGINAL_PUBLICATIONS_REQUIRED')
    read=_ports()[1];native=read(flat.observation_json,flat.observation_hash);initial=read(entry.observation_json,entry.observation_hash)
    protection=read(verified.observation_json,verified.observation_hash);identity=json.loads(claim.identity_json)
    raw=[effect['payload'] for effect in flat.effects if effect['kind']=='RAW_POSITION']
    if (claim.close_operation_id!=source['close_operation_id'] or identity['flat_publication_hash']!=flat.observation_hash or
            native.get('profile')!='product-close-native-observation-v0.2' or
            initial.get('profile')!='okx-product-position-readback-v0.2' or
            protection.get('profile')!='product-protection-observation-v0.2' or
            native['entry_operation_id']!=source['entry_operation_id'] or
            native['position']['provider_position_id']!=initial['provider_position_id'] or
            Decimal(native['position']['canonical_net_quantity'])!=0 or raw!=[source['raw_flat']] or
            flat.effects[-2]['payload']!=payload(baseline['current_position_projection'])):
        fail('FINALIZATION_ORIGINAL_FIRST_FLAT_PUBLICATION_REQUIRED')
    objects=[x for x in protection['inventory']['objects'] if x['provider_algo_id']==claim.native_algo_id]
    terminal=source['terminal_confirmation'];zero=source['native_confirmation'];inventory=source['inventory_confirmation']
    observed=parse_product_terminal_stop(dict(code='0',data=[terminal['row']]),prepared[1],
        received_at=_at(terminal['received_at']),expected_provider_id=claim.native_algo_id)
    if (observed.source_hash!=terminal['source_hash'] or
            len(objects)!=1 or observed.provider_created_at!=_at(objects[0]['provider_created_at']) or
            observed.provider_updated_at<_at(source['raw_flat']['broker_state_observed_at']) or
            zero['provider_position_id']!=initial['provider_position_id'] or Decimal(zero['canonical_net_quantity'])!=0 or
            _at(zero['provider_updated_at'])<_at(native['position']['provider_updated_at']) or
            inventory['objects'] or inventory['coverage']!='CONVERGED_BOUNDED_READ_SCAN' or
            inventory['algo_types']!=list(ALGO_TYPES) or inventory['request_count']!=16 or
            inventory['account_hash']!=protection['inventory']['account_hash'] or
            zero['metadata_hash']!=inventory['metadata_hash'] or zero['metadata_hash']!=source['metadata_hash']):
        fail('FINALIZATION_EXACT_TERMINAL_EMPTY_INVENTORY_AND_NATIVE_ZERO_REQUIRED')
    if len(baseline['funding_evidence'])!=1:fail('FINALIZATION_ONE_DURABLE_ALLOCATED_FUNDING_REQUIRED')
    evidence=payload(baseline['funding_evidence'][0])
    funding=journal.funding_publication(source['run_id'],source['close_operation_id'],_at(evidence['calculated_at']))
    if funding is None or funding.effects!=[dict(kind='FUNDING_EVIDENCE',payload=evidence)]:
        fail('FINALIZATION_ORIGINAL_DURABLE_ALLOCATED_FUNDING_REQUIRED')
    return dict(run_hash=digest(canonical(dict(run))),operations=operations,entry_publication=entry.observation_hash,
        flat_publication=flat.observation_hash,protection_publication=verified.observation_hash,
        cleanup_identity=claim.identity_hash,cleanup_source=claim.source_hash,
        funding_observation=funding.observation_hash,funding_effects=funding.effects_hash)


@dataclass(frozen=True)
class ProductFinalizationObservation:
    source_json:str
    effects_json:str


@dataclass(frozen=True)
class ProductFinalizationBatch:
    run_id:str
    operation_id:str
    stop_operation_id:str
    source_json:str
    source_hash:str
    effects_json:str
    effects_hash:str
    staged_at:str

    @property
    def source(self):return _ports()[1](self.source_json,self.source_hash)

    @property
    def effects(self):return _ports()[1](self.effects_json,self.effects_hash)


@dataclass(frozen=True)
class ProductFinalizationReceipt:
    run_id:str
    operation_id:str
    source_hash:str
    effects_hash:str
    closed_at:str
    interpreted_at:str
    published_at:str


def _batch(row):
    value=ProductFinalizationBatch(*(row[k] for k in ProductFinalizationBatch.__dataclass_fields__))
    if len(value.source_json)>1048576 or len(value.effects_json)>262144:fail('FINALIZATION_BOUNDED_BUNDLE_REQUIRED')
    source=value.source;effects=value.effects
    if (source.get('profile')!=PROFILE or source.get('run_id')!=value.run_id or source.get('close_operation_id')!=value.operation_id or
            source.get('stop_operation_id')!=value.stop_operation_id or not isinstance(effects,list) or
            len(effects)!=3 or any(type(x) is not dict or set(x)!={'kind','payload'} for x in effects) or
            [x['kind'] for x in effects]!=list(KINDS)):
        fail('FINALIZATION_EXACT_BUNDLE_REQUIRED')
    return value


def finalization_batch(journal,run_id,operation_id):
    journal._run(run_id)
    row=journal._db.execute('SELECT * FROM product_dispatch_finalization_outbox WHERE run_id=? AND operation_id=?',
        (run_id,operation_id)).fetchone()
    return None if row is None else _batch(row)


def finalization_receipt(journal,batch):
    if type(batch) is not ProductFinalizationBatch:fail('FINALIZATION_TYPED_ORIGINAL_BATCH_REQUIRED')
    row=journal._db.execute('SELECT * FROM product_dispatch_finalization_publications WHERE run_id=? AND operation_id=?',
        (batch.run_id,batch.operation_id)).fetchone()
    if row is None:return None
    if (row['source_hash'],row['effects_hash'])!=(batch.source_hash,batch.effects_hash):fail('FINALIZATION_EXACT_RECEIPT_REQUIRED')
    return ProductFinalizationReceipt(batch.run_id,batch.operation_id,batch.source_hash,batch.effects_hash,
        batch.effects[2]['payload']['closed_at'],batch.source['interpreted_at'],row['published_at'])


def stage_finalization(journal,canonical_journal,run_id,operation_id,observation,*,lease,clock,claim_inventory_generation):
    require_distinct_journals(journal,canonical_journal)
    if not callable(clock):fail('FINALIZATION_TRUSTED_CLOCK_REQUIRED')
    if type(observation) is not ProductFinalizationObservation:fail('FINALIZATION_TYPED_OBSERVATION_REQUIRED')
    if not isinstance(observation.source_json,str) or not isinstance(observation.effects_json,str):fail('FINALIZATION_SERIALIZED_SOURCE_AND_EFFECTS_REQUIRED')
    if len(observation.source_json)>1048576 or len(observation.effects_json)>262144:fail('FINALIZATION_BOUNDED_BUNDLE_REQUIRED')
    source=json.loads(observation.source_json);effects=json.loads(observation.effects_json);encode,_,stamp=_ports()
    if (source['run_id']!=run_id or source['close_operation_id']!=operation_id or
            encode(source)!=observation.source_json or encode(effects)!=observation.effects_json or build_effects(source)!=effects):
        fail('FINALIZATION_EXACT_E5_EFFECTS_REQUIRED')
    starts=[source['terminal_confirmation']['request_started_at'],source['native_confirmation']['received_at'],
        source['inventory_confirmation']['request_started_at'],source['metadata_observed_at']]
    def current_window():
        now=clock();at=stamp(now)
        if _at(source['interpreted_at'])>now or any(not _at(start)<=now<_at(start)+timedelta(seconds=5) for start in starts):
            fail('FINALIZATION_ORIGINAL_READ_WINDOW_EXPIRED')
        return at
    at=current_window()
    with journal._write():
        journal.require_claim_inventory_generation(claim_inventory_generation);journal._require_lease(run_id,lease,at)
        if original_refs(journal,source)!=source['original_refs'] or claim_snapshot(journal,run_id)!=source['claim_snapshot']:
            fail('FINALIZATION_ORIGINAL_SOURCE_CHANGED')
        if require_prefix(source,effects,recover_snapshot(canonical_journal,source))!=0:fail('FINALIZATION_UNPUBLISHED_BASELINE_REQUIRED')
        existing=finalization_batch(journal,run_id,operation_id)
        if existing is not None:fail('FINALIZATION_ORIGINAL_OUTBOX_ALREADY_EXISTS')
        # The semantic scans can consume the remaining original read window.
        # Sample again under the dispatch lock immediately before committing
        # durable replay authority; no source clock is renewed here.
        at=current_window();journal._require_lease(run_id,lease,at)
        journal._db.execute('INSERT INTO product_dispatch_finalization_outbox VALUES(?,?,?,?,?,?,?,?,?)',
            (run_id,operation_id,source['stop_operation_id'],observation.source_json,digest(observation.source_json),
                observation.effects_json,digest(observation.effects_json),at,lease.generation))
    return finalization_batch(journal,run_id,operation_id)


def pending_finalizations(journal,run_id):
    journal._run(run_id)
    rows=journal._db.execute('SELECT o.* FROM product_dispatch_finalization_outbox o LEFT JOIN product_dispatch_finalization_publications p '
        'ON p.run_id=o.run_id AND p.operation_id=o.operation_id WHERE o.run_id=? AND p.operation_id IS NULL ORDER BY o.operation_id LIMIT 100',
        (run_id,)).fetchall()
    return tuple(_batch(row) for row in rows)


def publish_finalization(journal,canonical_journal,batch,*,lease,clock):
    if type(batch) is not ProductFinalizationBatch or not callable(clock):fail('FINALIZATION_TYPED_ORIGINAL_BATCH_AND_CLOCK_REQUIRED')
    require_distinct_journals(journal,canonical_journal)
    source=batch.source;effects=batch.effects
    if build_effects(source)!=effects:fail('FINALIZATION_SAVED_E5_EFFECTS_MISMATCH')
    # The outbox was committed independently. Only this new transaction owns
    # the dispatch lock/receipt; canonical owners commit their individual facts.
    # No provider call, current-source publisher, or nested mark wrapper here.
    with journal._write():
        journal._require_lease(batch.run_id,lease,_ports()[2](clock()))
        if finalization_batch(journal,batch.run_id,batch.operation_id)!=batch:fail('FINALIZATION_ORIGINAL_BATCH_REQUIRED')
        if original_refs(journal,source)!=source['original_refs'] or claim_snapshot(journal,batch.run_id)!=source['claim_snapshot']:
            fail('FINALIZATION_ORIGINAL_SOURCE_CHANGED')
        current=recover_snapshot(canonical_journal,source);prefix=require_prefix(source,effects,current)
        for effect in effects[prefix:]:
            canonical_journal.publish_canonical_effects([effect])
            prefix+=1
            if require_prefix(source,effects,recover_snapshot(canonical_journal,source))!=prefix:
                fail('FINALIZATION_PREFIX_DID_NOT_ADVANCE')
        if require_prefix(source,effects,recover_snapshot(canonical_journal,source))!=3:fail('FINALIZATION_COMPLETE_READY_GRAPH_REQUIRED')
        if finalization_receipt(journal,batch) is None:
            journal._require_lease(batch.run_id,lease,_ports()[2](clock()))
            journal._db.execute('INSERT INTO product_dispatch_finalization_publications VALUES(?,?,?,?,?,?)',
                (batch.run_id,batch.operation_id,batch.source_hash,batch.effects_hash,_ports()[2](clock()),lease.generation))
    return finalization_receipt(journal,batch)
