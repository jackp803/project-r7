"""narrow original E2 EXIT data outbox draft.
Historical interpretation and publication receipts never issue dispatch authority.
Canonical provenance/earliest-fill selection remains the trusted exit owner's job.
"""
from dataclasses import dataclass, fields
from decimal import Decimal
import hashlib
import json

from registry.product_assessment import digest
from storage.product_entry_decision import _batch, _require_original, _utc, _utc_flexible
from position.exit_requests import CurrentExitAuthority, interpret_exit_request, anchor_exit_request
from position.exit_state import encode_exit_anchor, restore_exit_anchor
from position.lifecycle_execution_binding import validate_position_lifecycle_execution_evidence_binding
from position.entry_observation import product_entry_position_id
from strategy.v02.exits import ExitRequest
from market_data.current import MarketSnapshot
from execution.models import stable_position_action_client_order_id, stable_order_request_id

ANCHOR_PROFILE = 'product-original-exit-anchor-v0.2'
DECISION_PROFILE = 'product-original-exit-decision-v0.2'
_COMMON = {'profile','run_id','entry_decision_id','entry_evidence_hash','entry_operation_id',
           'original_exit_request','original_plan','source_position','source_binding','anchor'}
_ANCHOR_FIELDS = _COMMON
_DECISION_FIELDS = _COMMON | {'anchor_evidence_hash','market_snapshot',
    'market_freshness_classification','interpreted_at','action_expires_at',
    'position_action','operation_id'}


def _ports():
    from storage.product_dispatch import ProductDispatchError, _json, _read, _stamp
    return ProductDispatchError, _json, _read, _stamp


def _fail(code): raise _ports()[0](code)


def encode_exit_market(value):
    if type(value) is not MarketSnapshot: _fail('EXIT_ACTUAL_MARKET_SNAPSHOT_REQUIRED')
    result = {}
    for field in fields(MarketSnapshot):
        item = getattr(value,field.name)
        if field.name in ('observed_at','received_at'): item = _ports()[3](item)
        elif field.name in ('last_price','best_bid','best_ask') and item is not None: item = str(item)
        result[field.name] = item
    restore_exit_market(result)
    return result


def restore_exit_market(value):
    if type(value) is not dict or set(value) != {f.name for f in fields(MarketSnapshot)}:
        _fail('EXIT_EXACT_MARKET_FIELDS_REQUIRED')
    restored = dict(value)
    for name in ('last_price','best_bid','best_ask'):
        item = restored[name]
        if item is not None:
            if not isinstance(item,str) or len(item)>128: _fail('EXIT_MARKET_DECIMAL_REQUIRED')
            restored[name] = Decimal(item)
    for name in ('observed_at','received_at'): restored[name] = _utc(restored[name])
    if restored['freshness_ms'] is not None and type(restored['freshness_ms']) is not int:
        _fail('EXIT_MARKET_FRESHNESS_INTEGER_REQUIRED')
    for name in ('schema_version','symbol','health_status','source'):
        if not isinstance(restored[name],str) or not restored[name] or len(restored[name])>256:
            _fail('EXIT_MARKET_BOUNDED_TEXT_REQUIRED')
    return MarketSnapshot(**restored)


def _base(value, *, decision=False):
    if (type(value) is not dict or set(value) != (_DECISION_FIELDS if decision else _ANCHOR_FIELDS)
            or value['profile'] != (DECISION_PROFILE if decision else ANCHOR_PROFILE)):
        _fail('EXIT_EXACT_EVIDENCE_REQUIRED')
    request = ExitRequest(_ports()[1](value['original_exit_request']))
    source = value['source_position']; plan = value['original_plan']
    validate_position_lifecycle_execution_evidence_binding(value['source_binding'],source)
    if (source['position_id'] != product_entry_position_id(plan['trade_plan_id'])
            or source['lifecycle_state'] not in ('OPEN_UNPROTECTED','OPEN_PROTECTED')
            or Decimal(source['actual_quantity']) <= 0):
        _fail('EXIT_ORIGINAL_POSITIVE_SOURCE_REQUIRED')
    anchor = restore_exit_anchor(value['anchor'],request=request,position=source,plan=plan)
    return request, source, plan, anchor


@dataclass(frozen=True)
class ProductExitObservation:
    evidence_json: str


@dataclass(frozen=True)
class ProductExitAnchor:
    run_id: str
    entry_decision_id: str
    evidence_json: str
    evidence_hash: str

    @property
    def evidence(self):
        value = _ports()[2](self.evidence_json,self.evidence_hash)
        request,source,plan,anchor = _base(value)
        if (value['run_id'],value['entry_decision_id']) != (self.run_id,self.entry_decision_id):
            _fail('EXIT_EXACT_ANCHOR_SUBJECT_REQUIRED')
        # First immutable anchor is the original, unadvanced E5 first-fill anchor.
        if encode_exit_anchor(anchor_exit_request(request,source,plan)) != value['anchor']:
            _fail('EXIT_ORIGINAL_FIRST_FILL_ANCHOR_REQUIRED')
        return value

    @property
    def anchor(self):
        value = self.evidence
        return _base(value)[3]


@dataclass(frozen=True)
class ProductExitDecision:
    run_id: str
    entry_decision_id: str
    decision_id: str
    evidence_json: str
    evidence_hash: str
    effects_hash: str

    @property
    def evidence(self):
        value = _ports()[2](self.evidence_json,self.evidence_hash)
        request,source,plan,anchor = _base(value,decision=True)
        if (value['run_id'],value['entry_decision_id']) != (self.run_id,self.entry_decision_id):
            _fail('EXIT_EXACT_DECISION_SUBJECT_REQUIRED')
        at = _utc(value['interpreted_at']); expiry = _utc(value['action_expires_at'])
        if _utc_flexible(source['lifecycle_interpreted_at']) > at: _fail('EXIT_FUTURE_SOURCE_REQUIRED')
        outcome = interpret_exit_request(request,CurrentExitAuthority(source,plan,anchor,
            restore_exit_market(value['market_snapshot']),value['market_freshness_classification'],at,expiry))
        if (outcome.status != 'AUTHORIZED' or outcome.lifecycle_intent != 'EXIT_REQUESTED'
                or outcome.position_action != value['position_action']
                or value['position_action'].get('action') != 'EXIT'):
            _fail('EXIT_ORIGINAL_AUTHORIZED_ACTION_REQUIRED')
        operation = stable_order_request_id(stable_position_action_client_order_id(
            value['position_action']['position_action_id'],'POSITION_EXIT'))
        if value['operation_id'] != operation or self.decision_id != _decision_id(value):
            _fail('EXIT_ORIGINAL_OPERATION_REQUIRED')
        return value

    @property
    def effects(self):
        from storage._runtime_validation import immutable_object_metadata
        action = self.evidence['position_action']
        immutable_object_metadata('POSITION_ACTION',action)
        result = [{'kind':'POSITION_ACTION','payload':action}]
        if digest(_ports()[1](result)) != self.effects_hash: _fail('EXIT_EXACT_EFFECT_HASH_REQUIRED')
        return result


def _decision_id(value):
    material = [value['run_id'],value['entry_decision_id'],value['position_action']['position_action_id']]
    return 'exit_' + hashlib.sha256(_ports()[1](material).encode('utf-8')).hexdigest()


def _entry(journal,value):
    journal._run(value['run_id'])
    row = journal._db.execute('SELECT * FROM product_entry_decisions WHERE run_id=? AND decision_id=?',
        (value['run_id'],value['entry_decision_id'])).fetchone()
    if row is None: _fail('EXIT_ORIGINAL_ENTRY_REQUIRED')
    entry = _batch(row); _require_original(journal,entry)
    if (entry.evidence['status'] != 'APPROVE' or entry.evidence_hash != value['entry_evidence_hash']
            or entry.evidence['operation_id'] != value['entry_operation_id']
            or entry.exit_request != value['original_exit_request']
            or entry.effects[1]['payload'] != value['original_plan']):
        _fail('EXIT_EXACT_ORIGINAL_ENTRY_REQUIRED')
    operation = journal.operation(entry.run_id,value['entry_operation_id'])
    if (operation is None or operation.status == 'PREPARED' or operation.request.get('role') != 'ENTRY'):
        _fail('EXIT_ACTUAL_CLAIMED_ENTRY_REQUIRED')
    # Canonical positive source and original fill membership are checked by owner,
    # not inferred from ACK/dispatch claim or this immutable interchange record.
    return entry


def _anchor_row(row):
    obj = ProductExitAnchor(*(row[k] for k in ('run_id','entry_decision_id','evidence_json','evidence_hash')))
    obj.anchor
    return obj


def _decision_row(row):
    obj = ProductExitDecision(*(row[k] for k in ('run_id','entry_decision_id','decision_id',
        'evidence_json','evidence_hash','effects_hash')))
    obj.effects
    return obj


def exit_anchor(journal,run_id,entry_decision_id):
    journal._run(run_id)
    row = journal._db.execute('SELECT * FROM product_exit_anchors WHERE run_id=? AND entry_decision_id=?',
        (run_id,entry_decision_id)).fetchone()
    if row is None: return None
    obj = _anchor_row(row); _entry(journal,obj.evidence)
    return obj


def _require_anchor(journal,obj):
    value = obj.evidence; _entry(journal,value)
    anchor = exit_anchor(journal,obj.run_id,obj.entry_decision_id)
    if anchor is None or anchor.evidence_hash != value['anchor_evidence_hash']:
        _fail('EXIT_DURABLE_ORIGINAL_ANCHOR_REQUIRED')
    for name in ('entry_evidence_hash','entry_operation_id','original_exit_request','original_plan','anchor'):
        if value[name] != anchor.evidence[name]: _fail('EXIT_ORIGINAL_ANCHOR_CONFLICT')
    source = value['source_position']; first = anchor.evidence['source_position']
    if (source['opened_at'] != first['opened_at'] or source['position_id'] != first['position_id']
            or source['lifecycle_revision'] < first['lifecycle_revision']):
        _fail('EXIT_ORIGINAL_SOURCE_LINEAGE_REQUIRED')


def exit_decision(journal,run_id,entry_decision_id):
    journal._run(run_id)
    row = journal._db.execute('SELECT * FROM product_exit_decisions WHERE run_id=? AND entry_decision_id=?',
        (run_id,entry_decision_id)).fetchone()
    if row is None: return None
    obj = _decision_row(row); _require_anchor(journal,obj)
    return obj


def _material(raw):
    if type(raw) is not str or len(raw.encode('utf-8'))>262144: _fail('EXIT_BOUNDED_EVIDENCE_REQUIRED')
    return _ports()[1](json.loads(raw))


def stage_exit_anchor(journal,run_id,entry_decision_id,evidence_json,*,lease,now):
    raw = _material(evidence_json)
    obj = ProductExitAnchor(run_id,entry_decision_id,raw,digest(raw)); value = obj.evidence
    _entry(journal,value)
    if _utc_flexible(value['source_position']['lifecycle_interpreted_at']) > now:
        _fail('EXIT_ANCHOR_FUTURE_SOURCE_REQUIRED')
    with journal._write():
        journal._require_lease(run_id,lease,_ports()[3](now)); _entry(journal,value)
        old = exit_anchor(journal,run_id,entry_decision_id)
        if old is not None:
            if old != obj: _fail('EXIT_ANCHOR_IMMUTABLE_CONFLICT')
            return old
        journal._db.execute('INSERT INTO product_exit_anchors VALUES(?,?,?,?,?,?)',
            (run_id,entry_decision_id,raw,obj.evidence_hash,lease.generation,_ports()[3](now)))
    return exit_anchor(journal,run_id,entry_decision_id)


def stage_exit_decision(journal,run_id,entry_decision_id,evidence_json,*,lease,now):
    raw = _material(evidence_json); value = json.loads(raw)
    effect_hash = digest(_ports()[1]([{'kind':'POSITION_ACTION','payload':value['position_action']}]))
    obj = ProductExitDecision(run_id,entry_decision_id,_decision_id(value),raw,digest(raw),effect_hash)
    obj.effects; _require_anchor(journal,obj)
    if _utc(value['interpreted_at']) > now: _fail('EXIT_FUTURE_INTERPRETATION_REQUIRED')
    with journal._write():
        journal._require_lease(run_id,lease,_ports()[3](now)); _require_anchor(journal,obj)
        old = exit_decision(journal,run_id,entry_decision_id)
        if old is not None:
            if old != obj: _fail('EXIT_FIRST_DECISION_IMMUTABLE_CONFLICT')
            return old
        journal._db.execute('INSERT INTO product_exit_decisions VALUES(?,?,?,?,?,?,?,?,?)',
            (run_id,entry_decision_id,obj.decision_id,raw,obj.evidence_hash,obj.effects_hash,
             value['anchor_evidence_hash'],lease.generation,_ports()[3](now)))
    return exit_decision(journal,run_id,entry_decision_id)


def pending_exit_publications(journal,run_id):
    journal._run(run_id)
    rows = journal._db.execute('SELECT o.* FROM product_exit_decisions o LEFT JOIN product_exit_publications p '
        'USING(run_id,entry_decision_id) WHERE o.run_id=? AND p.run_id IS NULL '
        'ORDER BY o.entry_decision_id LIMIT 1000',(run_id,)).fetchall()
    result = tuple(_decision_row(row) for row in rows)
    for obj in result: _require_anchor(journal,obj)
    return result


def mark_exit_publication(journal,batch,*,lease,now):
    if type(batch) is not ProductExitDecision: _fail('EXIT_EXACT_PUBLICATION_REQUIRED')
    with journal._write():
        journal._require_lease(batch.run_id,lease,_ports()[3](now))
        old = exit_decision(journal,batch.run_id,batch.entry_decision_id)
        if old != batch or _utc(batch.evidence['interpreted_at']) > now:
            _fail('EXIT_EXACT_PUBLICATION_REQUIRED')
        row = journal._db.execute('SELECT * FROM product_exit_publications WHERE run_id=? AND entry_decision_id=?',
            (batch.run_id,batch.entry_decision_id)).fetchone()
        if row is not None:
            if (row['decision_id'],row['evidence_hash'],row['effects_hash']) != (
                    batch.decision_id,batch.evidence_hash,batch.effects_hash):
                _fail('EXIT_EXACT_PUBLICATION_REQUIRED')
            return
        journal._db.execute('INSERT INTO product_exit_publications VALUES(?,?,?,?,?,?,?)',
            (batch.run_id,batch.entry_decision_id,batch.decision_id,batch.evidence_hash,
             batch.effects_hash,lease.generation,_ports()[3](now)))
