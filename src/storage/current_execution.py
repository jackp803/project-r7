"""Readonly exact canonical E6 subject snapshots; data never grants an effect."""
from dataclasses import dataclass
from registry.models import StrategyIdentity
from storage.runtime_models import RuntimeValidationError, StoredCanonicalObject
from storage._runtime_validation import canonical_payload, immutable_object_metadata


@dataclass(frozen=True)
class CurrentExecutionSubject:
    identity: StrategyIdentity
    risk_decision: StoredCanonicalObject
    approved_trade_plan: StoredCanonicalObject
    current_position_projection: StoredCanonicalObject | None = None
    current_lifecycle_execution_binding: StoredCanonicalObject | None = None
    position_action: StoredCanonicalObject | None = None


def _invalid():
    raise RuntimeValidationError('CURRENT_CANONICAL_EXECUTION_SUBJECT_UNAVAILABLE',
                                 'Exact current durable canonical execution subject required') from None


def _checked(journal, kind, canonical_id):
    row = journal._store._object_row(kind, canonical_id)
    if row is None:
        _invalid()
    try:
        payload = journal._store._row_payload(row)
        journal._check_payload_policy(payload)
        _, raw, hashed = canonical_payload(payload)
        if raw != row['payload_json'] or hashed != row['payload_hash']:
            _invalid()
        metadata = immutable_object_metadata(kind, payload)
        if metadata['canonical_id'] != canonical_id:
            _invalid()
    except (ValueError, TypeError, KeyError):
        _invalid()
    return StoredCanonicalObject(kind, canonical_id, raw, hashed)


def current_execution_subject(journal, identity, trade_plan_id, *, position_id=None, position_action_id=None):
    if (type(identity) is not StrategyIdentity or not isinstance(trade_plan_id, str) or not trade_plan_id or
        len(trade_plan_id) > 256 or (position_id is None) != (position_action_id is None)):
        _invalid()
    connection = journal._store._connection
    if connection.in_transaction:
        _invalid()
    connection.execute('BEGIN')
    try:
        plan = _checked(journal, 'APPROVED_TRADE_PLAN', trade_plan_id)
        material = plan.payload
        if (material['strategy_id'], material['strategy_version']) != (identity.strategy_id, identity.strategy_version):
            _invalid()
        risk = _checked(journal, 'RISK_DECISION', material['risk_decision_id'])
        decision = risk.payload
        if (decision.get('decision') != 'APPROVE' or
            any(decision.get(field) != material.get(field) for field in ('strategy_id', 'strategy_version', 'intent_id', 'risk_policy_version'))):
            _invalid()
        if position_id is None:
            return CurrentExecutionSubject(identity, risk, plan)
        if not all(isinstance(value, str) and value and len(value) <= 256 for value in (position_id, position_action_id)):
            _invalid()
        action = _checked(journal, 'POSITION_ACTION', position_action_id)
        if (action.payload.get('position_id') != position_id or action.payload.get('trade_plan_id') != trade_plan_id or
            action.payload.get('risk_decision_id') != material['risk_decision_id']):
            _invalid()
        recovered = journal.recover(position_id=position_id, trade_plan_id=trade_plan_id)
        if (not recovered.restart_authoritative or recovered.current_position_projection is None or
            recovered.current_lifecycle_execution_binding is None or recovered.approved_trade_plan != plan or
            recovered.risk_decision != risk):
            _invalid()
        return CurrentExecutionSubject(identity, risk, plan, recovered.current_position_projection,
                                        recovered.current_lifecycle_execution_binding, action)
    finally:
        connection.rollback()


def require_current_execution_subject(journal, snapshot):
    if type(snapshot) is not CurrentExecutionSubject:
        _invalid()
    position_id = None if snapshot.position_action is None else snapshot.position_action.payload.get('position_id')
    action_id = None if snapshot.position_action is None else snapshot.position_action.canonical_id
    fresh = current_execution_subject(journal, snapshot.identity, snapshot.approved_trade_plan.canonical_id,
                                      position_id=position_id, position_action_id=action_id)
    if fresh != snapshot:
        _invalid()
    return fresh
