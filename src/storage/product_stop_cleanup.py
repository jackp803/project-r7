"""One immutable local stop-cleanup claim; never a submit permission or ACK."""
from dataclasses import dataclass
from decimal import Decimal,InvalidOperation
import json
import re

from brokers.okx_product_state import restore_product_readback
from storage.product_position import latest_position_publication

PROFILE='fixture-owned-unused-stop-cleanup-v0.2'


def _zero(value):
    if not isinstance(value,str) or len(value)>128:return False
    try:
        quantity=Decimal(value)
        return quantity.is_finite() and quantity==0
    except InvalidOperation:return False


def _ports():
    from storage.product_dispatch import ProductDispatchError,_json,_read,_stamp
    return ProductDispatchError,_json,_read,_stamp


@dataclass(frozen=True)
class ProductStopCleanupClaim:
    run_id:str
    stop_operation_id:str
    close_operation_id:str
    native_algo_id:str
    identity_json:str
    identity_hash:str
    source_json:str
    source_hash:str


def stop_cleanup_claim(journal,run_id,stop_operation_id):
    journal._run(run_id);Error,_,read,_=_ports()
    row=journal._db.execute('SELECT * FROM product_dispatch_stop_cleanup_claims WHERE run_id=? AND stop_operation_id=?',
        (run_id,stop_operation_id)).fetchone()
    if row is None:return None
    identity=read(row['identity_json'],row['identity_hash']);source=read(row['source_json'],row['source_hash'])
    if (type(identity) is not dict or identity.get('profile')!=PROFILE or type(source) is not dict or
            source.get('profile')!='fixture-stop-cleanup-read-evidence-v0.2' or
            any(identity.get(key)!=row[key] for key in ('run_id','stop_operation_id','close_operation_id','native_algo_id','provider_ref','account_ref'))):
        raise Error('STOP_CLEANUP_ORIGINAL_CLAIM_CORRUPT')
    return ProductStopCleanupClaim(*(row[k] for k in ('run_id','stop_operation_id','close_operation_id','native_algo_id',
        'identity_json','identity_hash','source_json','source_hash')))


def claim_stop_cleanup(journal,run_id,stop_operation_id,close_operation_id,native_algo_id,flat_publication_hash,
        source,*,lease,now,claim_inventory_generation):
    Error,encode,read,stamp=_ports();at=stamp(now)
    if (not isinstance(native_algo_id,str) or not re.fullmatch('[0-9]{1,64}',native_algo_id) or
            type(source) is not dict or source.get('profile')!='fixture-stop-cleanup-read-evidence-v0.2'):
        raise Error('STOP_CLEANUP_EXACT_SOURCE_REQUIRED')
    source_json=encode(source)
    from registry.product_assessment import digest
    with journal._write():
        journal.require_claim_inventory_generation(claim_inventory_generation)
        run=journal._run(run_id);journal._require_lease(run_id,lease,at)
        if journal._db.execute('SELECT namespace FROM product_dispatch_namespace WHERE singleton=1').fetchone()[0]!='FIXTURE':
            raise Error('STOP_CLEANUP_FIXTURE_PROFILE_ONLY')
        stop=journal.operation(run_id,stop_operation_id);close=journal.operation(run_id,close_operation_id)
        if stop is None or close is None or any(op.recovery_disposition!='READBACK_REQUIRED' for op in (stop,close)):
            raise Error('STOP_CLEANUP_ORIGINAL_CLAIMS_REQUIRED')
        stop_request=restore_product_readback(stop.request);close_request=restore_product_readback(close.request)
        flat=latest_position_publication(journal,run_id,close_operation_id)
        verified=latest_position_publication(journal,run_id,stop_operation_id)
        if (stop_request.role!='PROTECTION_STOP' or close_request.role not in ('POSITION_EXIT','EMERGENCY_EXIT') or
                stop_request.canonical_request.position_id!=close_request.canonical_request.position_id or
                stop_request.canonical_request.trade_plan_id!=close_request.canonical_request.trade_plan_id or
                flat is None or verified is None or flat.observation_hash!=flat_publication_hash or flat.observed_at>at):
            raise Error('STOP_CLEANUP_ORIGINAL_FLAT_AND_PROTECTION_REQUIRED')
        flat_material=read(flat.observation_json,flat.observation_hash);protection=read(verified.observation_json,verified.observation_hash)
        if (flat_material.get('profile')!='product-close-native-observation-v0.2' or
                not _zero(flat_material['position']['canonical_net_quantity']) or
                protection.get('profile')!='product-protection-observation-v0.2' or
                json.loads(stop.observation_json or '{}').get('provider_id')!=native_algo_id):
            raise Error('STOP_CLEANUP_ORIGINAL_NATIVE_LINEAGE_REQUIRED')
        identity=dict(profile=PROFILE,run_id=run_id,stop_operation_id=stop_operation_id,close_operation_id=close_operation_id,
            native_algo_id=native_algo_id,flat_publication_hash=flat_publication_hash,
            stop_request_hash=digest(stop.request_json),provider_ref=run['provider_ref'],account_ref=run['account_ref'])
        raw=encode(identity);existing=stop_cleanup_claim(journal,run_id,stop_operation_id)
        if existing is not None:
            if existing.identity_json!=raw:raise Error('STOP_CLEANUP_ORIGINAL_CLAIM_CONFLICT')
            return False
        journal._db.execute('INSERT INTO product_dispatch_stop_cleanup_claims VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (run_id,stop_operation_id,close_operation_id,native_algo_id,run['provider_ref'],run['account_ref'],raw,digest(raw),
                source_json,digest(source_json),at,lease.generation))
    return True
