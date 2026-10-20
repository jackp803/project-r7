"""narrow immutable E6 entry interpretation outbox.

Historical E2/E5 output is data, never a runtime permit or provider capability.
No canonical SQLite writer is entered from an E6 writer transaction.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re

from execution.models import stable_client_order_id, stable_order_request_id
from registry.product_assessment import digest
from risk.product_policy import parse_product_risk_policy
from risk.engine import require_approved_trade_plan_binding
from storage._runtime_validation import immutable_object_metadata

PROFILE = 'product-entry-decision-v0.2'
_FIELDS = {'profile','namespace','run_id','strategy_id','strategy_version','strategy_content_hash',
    'owner_binding_hash','boundary','information_cutoff','availability_model','input_hash',
    'selected_risk_policy','risk_context','risk_proposal','signal','exit_request','trade_intent',
    'interpreted_at','status','operation_id'}


def _ports():
    from storage.product_dispatch import ProductDispatchError, _json, _read, _stamp, _text
    return ProductDispatchError, _json, _read, _stamp, _text


def _utc(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        raise _ports()[0]('ENTRY_DECISION_UTC_REQUIRED')
    at = datetime.fromisoformat(value.replace('Z','+00:00'))
    if _ports()[3](at) != value:
        raise _ports()[0]('ENTRY_DECISION_CANONICAL_UTC_REQUIRED')
    return at


def entry_decision_id(run_id, strategy_id, strategy_version, boundary):
    _, encode, _, stamp, text = _ports()
    raw = encode([text(run_id),text(strategy_id),text(strategy_version),stamp(boundary)])
    return 'entry_' + hashlib.sha256(raw.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class ProductEntryObservation:
    evidence_json: str
    effects_json: str


@dataclass(frozen=True)
class ProductEntryDecision:
    run_id: str
    boundary_text: str
    decision_id: str
    evidence_json: str
    evidence_hash: str
    effects_json: str
    effects_hash: str

    @property
    def evidence(self):
        Error, encode, read, _, _ = _ports()
        value = read(self.evidence_json, self.evidence_hash)
        if type(value) is not dict or set(value) != _FIELDS or value['profile'] != PROFILE:
            raise Error('ENTRY_EXACT_DECISION_REQUIRED')
        if (value['run_id'] != self.run_id or value['boundary'] != self.boundary_text or
                value['availability_model'] != 'recorded_received_at' or
                value['namespace'] not in ('FIXTURE','LOCAL_RESEARCH') or
                value['status'] not in ('NO_TRADE','REJECT','APPROVE')):
            raise Error('ENTRY_EXACT_DECISION_REQUIRED')
        boundary = _utc(value['boundary']); cutoff = _utc(value['information_cutoff'])
        interpreted = _utc(value['interpreted_at'])
        if boundary > interpreted or cutoff > interpreted:
            raise Error('ENTRY_FUTURE_INTERPRETATION_REQUIRED')
        for key in ('strategy_content_hash','owner_binding_hash','input_hash'):
            if not isinstance(value[key],str) or not re.fullmatch('sha256:[0-9a-f]{64}',value[key]):
                raise Error('ENTRY_EXACT_INPUT_COMMITMENT_REQUIRED')
        if self.decision_id != entry_decision_id(self.run_id,value['strategy_id'],value['strategy_version'],boundary):
            raise Error('ENTRY_EXACT_DECISION_ID_REQUIRED')
        policy = parse_product_risk_policy(value['selected_risk_policy'],namespace=value['namespace'])
        signal = value['signal']
        if (type(signal) is not dict or
                any(signal.get(k) != value[k] for k in ('strategy_id','strategy_version','strategy_content_hash')) or
                _utc_flexible(signal['evaluated_at']) != boundary or
                not re.fullmatch('sha256:[0-9a-f]{64}',signal.get('market_boundary_ref',''))):
            raise Error('ENTRY_EXACT_E2_SUBJECT_REQUIRED')
        # Validate the persisted E2 exit profile with its existing owner type.
        if value['status'] == 'NO_TRADE':
            if signal.get('direction') != 'NO_TRADE' or any(value[k] is not None for k in ('exit_request','trade_intent','operation_id')):
                raise Error('ENTRY_NO_TRADE_ZERO_EFFECTS_REQUIRED')
        else:
            from strategy.v02.exits import ExitRequest
            from position.exit_requests import resolve_exit_constraints
            from strategy.trade_intent import build_trade_intent
            request = ExitRequest(encode(value['exit_request']))
            exit_value = request.as_dict()
            if (any(exit_value[k] != value[k] for k in ('strategy_id','strategy_version','strategy_content_hash')) or
                    any(exit_value[k] != signal.get(k) for k in ('symbol','direction','market_boundary_ref','reference_price')) or
                    _utc_flexible(exit_value['observed_at']) != boundary):
                raise Error('ENTRY_EXACT_E2_EXIT_REQUIRED')
            intent = value['trade_intent']
            if (type(intent) is not dict or signal.get('direction') not in ('LONG','SHORT') or
                    any(intent.get(k) != value[k] for k in ('strategy_id','strategy_version')) or
                    intent.get('direction') != signal['direction']):
                raise Error('ENTRY_EXACT_E2_INTENT_REQUIRED')
            constraints = resolve_exit_constraints(request)
            original_intent = build_trade_intent(signal,entry_profile_version='entry-v0.1',
                entry_order_type='MARKET',generated_at=boundary,
                strategy_stop_level=constraints.stop_level,strategy_target_level=constraints.target_level,
                max_hold_seconds=constraints.max_hold_seconds)
            if intent != original_intent:
                raise Error('ENTRY_EXACT_E2_INTENT_REQUIRED')
        return value

    @property
    def effects(self):
        Error, _, read, _, _ = _ports()
        value = self.evidence
        effects = read(self.effects_json,self.effects_hash)
        expected = {'NO_TRADE': [], 'REJECT':['RISK_DECISION'],
                    'APPROVE':['RISK_DECISION','APPROVED_TRADE_PLAN']}[value['status']]
        if (type(effects) is not list or len(effects) != len(expected) or
                any(type(e) is not dict or set(e) != {'kind','payload'} or e['kind'] != kind or
                    type(e['payload']) is not dict for e,kind in zip(effects,expected))):
            raise Error('ENTRY_EXACT_E5_EFFECTS_REQUIRED')
        for effect in effects:
            immutable_object_metadata(effect['kind'],effect['payload'])
            if any(effect['payload'][k] != value[k] for k in ('strategy_id','strategy_version')):
                raise Error('ENTRY_EXACT_E5_SUBJECT_REQUIRED')
        if effects:
            risk = effects[0]['payload']
            if (risk['decision'] != value['status'] or risk['intent_id'] != value['trade_intent']['intent_id'] or
                    _ports()[3](_utc_flexible(risk['decided_at'])) != value['interpreted_at']):
                raise Error('ENTRY_ORIGINAL_E5_CLOCK_REQUIRED')
            if value['status'] == 'APPROVE':
                plan = effects[1]['payload']
                policy = parse_product_risk_policy(value['selected_risk_policy'],namespace=value['namespace'])
                require_approved_trade_plan_binding(risk,plan,policy.risk_policy)
                operation = stable_order_request_id(stable_client_order_id(plan['trade_plan_id'],'entry'))
                if (operation != value['operation_id'] or plan['intent_id'] != value['trade_intent']['intent_id'] or
                        _ports()[3](_utc_flexible(plan['created_at'])) != value['interpreted_at']):
                    raise Error('ENTRY_ORIGINAL_PLAN_REQUIRED')
            elif value['operation_id'] is not None:
                raise Error('ENTRY_REJECT_ZERO_OPERATION_REQUIRED')
        return effects

    @property
    def boundary(self): return _utc(self.boundary_text)
    @property
    def signal(self): return self.evidence['signal']
    @property
    def trade_intent(self): return self.evidence['trade_intent']
    @property
    def exit_request(self): return self.evidence['exit_request']
    @property
    def strategy_content_hash(self): return self.evidence['strategy_content_hash']


def _utc_flexible(value):
    at = datetime.fromisoformat(value.replace('Z','+00:00'))
    _ports()[3](at)
    return at


def _batch(row):
    batch = ProductEntryDecision(*(row[k] for k in ('run_id','boundary','decision_id','evidence_json',
        'evidence_hash','effects_json','effects_hash')))
    batch.effects
    return batch


def _require_original(journal,batch):
    Error, _, read, _, _ = _ports()
    run = journal._run(batch.run_id); binding = read(run['binding_json'],run['binding_hash'])
    value = batch.evidence
    if (value['owner_binding_hash'] != run['binding_hash'] or
            binding['namespace'] != value['namespace'] or
            binding['identity'] != dict(strategy_id=value['strategy_id'],strategy_version=value['strategy_version']) or
            binding['strategy_content_hash'] != value['strategy_content_hash']):
        raise Error('ENTRY_ORIGINAL_OWNER_BINDING_REQUIRED')
    policy = parse_product_risk_policy(value['selected_risk_policy'],namespace=value['namespace'])
    release = binding['release']
    if (policy.policy_hash != release['risk_policy_hash'] or
            value['selected_risk_policy']['generation'] != release['risk_generation']):
        raise Error('ENTRY_ORIGINAL_SELECTED_POLICY_REQUIRED')


def entry_decision(journal,run_id,identity,boundary):
    journal._run(run_id)
    row = journal._db.execute('SELECT * FROM product_entry_decisions WHERE run_id=? AND boundary=?',
        (run_id,_ports()[3](boundary))).fetchone()
    if row is None: return None
    batch = _batch(row); value = batch.evidence
    if (value['strategy_id'],value['strategy_version']) != (identity.strategy_id,identity.strategy_version):
        raise _ports()[0]('ENTRY_EXACT_BOUNDARY_SUBJECT_REQUIRED')
    _require_original(journal,batch)
    return batch


def stage_entry_decision(journal,run_id,identity,boundary,observation,*,lease,now):
    Error, encode, _, stamp, _ = _ports()
    if type(observation) is not ProductEntryObservation:
        raise Error('ENTRY_INTERNAL_OBSERVATION_REQUIRED')
    # Only bounded E2/E5 outputs are persisted. E1 history is streamed into input_hash.
    raw = encode(json.loads(observation.evidence_json)); effects = encode(json.loads(observation.effects_json))
    decision = entry_decision_id(run_id,identity.strategy_id,identity.strategy_version,boundary)
    batch = ProductEntryDecision(run_id,stamp(boundary),decision,raw,digest(raw),effects,digest(effects))
    batch.effects; _require_original(journal,batch)
    if batch.evidence['interpreted_at'] > stamp(now): raise Error('ENTRY_INTERPRETATION_CLOCK_REQUIRED')
    with journal._write():
        journal._require_lease(run_id,lease,stamp(now)); _require_original(journal,batch)
        old = entry_decision(journal,run_id,identity,boundary)
        if old is not None:
            if old != batch: raise Error('ENTRY_BOUNDARY_INPUT_CONFLICT')
            return old
        journal._db.execute('INSERT INTO product_entry_decisions VALUES(?,?,?,?,?,?,?,?,?)',
            (batch.run_id,batch.boundary_text,batch.decision_id,batch.evidence_json,batch.evidence_hash,
             batch.effects_json,batch.effects_hash,lease.generation,stamp(now)))
    return entry_decision(journal,run_id,identity,boundary)


def pending_entry_publications(journal,run_id):
    journal._run(run_id)
    batches = tuple(_batch(row) for row in journal._db.execute(
        'SELECT o.* FROM product_entry_decisions o LEFT JOIN product_entry_publications p '
        'USING(run_id,boundary) WHERE o.run_id=? AND p.run_id IS NULL '
        'ORDER BY o.boundary,o.decision_id LIMIT 1000',(run_id,)).fetchall())
    for batch in batches: _require_original(journal,batch)
    return batches


def mark_entry_publication(journal,batch,*,lease,now):
    Error, _, _, stamp, _ = _ports()
    if type(batch) is not ProductEntryDecision: raise Error('ENTRY_EXACT_PUBLICATION_REQUIRED')
    with journal._write():
        journal._require_lease(batch.run_id,lease,stamp(now)); _require_original(journal,batch)
        row = journal._db.execute('SELECT * FROM product_entry_decisions WHERE run_id=? AND boundary=?',
            (batch.run_id,batch.boundary_text)).fetchone()
        if row is None or _batch(row) != batch or stamp(now) < batch.evidence['interpreted_at']:
            raise Error('ENTRY_EXACT_PUBLICATION_REQUIRED')
        old = journal._db.execute('SELECT * FROM product_entry_publications WHERE run_id=? AND boundary=?',
            (batch.run_id,batch.boundary_text)).fetchone()
        if old is not None:
            if (old['decision_id'],old['effects_hash']) != (batch.decision_id,batch.effects_hash):
                raise Error('ENTRY_EXACT_PUBLICATION_REQUIRED')
            return
        journal._db.execute('INSERT INTO product_entry_publications VALUES(?,?,?,?,?,?,?)',
            (batch.run_id,batch.boundary_text,batch.decision_id,batch.effects_hash,lease.generation,
             stamp(now),batch.evidence_hash))
