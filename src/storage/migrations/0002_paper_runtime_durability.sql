PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS paper_runtime_objects (
    object_kind TEXT NOT NULL
        CHECK (object_kind IN ('RISK_DECISION', 'APPROVED_TRADE_PLAN', 'POSITION_ACTION', 'ORDER_REQUEST', 'FILL')),
    canonical_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    strategy_id TEXT,
    strategy_version TEXT,
    trade_plan_id TEXT,
    position_id TEXT,
    order_request_id TEXT,
    client_order_id TEXT,
    broker_order_id TEXT,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (object_kind, canonical_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS paper_runtime_order_request_client_id_uq
ON paper_runtime_objects(client_order_id)
WHERE object_kind = 'ORDER_REQUEST' AND client_order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS paper_runtime_objects_trade_plan_idx
ON paper_runtime_objects(trade_plan_id, object_kind, canonical_id);

CREATE INDEX IF NOT EXISTS paper_runtime_objects_position_idx
ON paper_runtime_objects(position_id, object_kind, canonical_id);

CREATE TRIGGER IF NOT EXISTS paper_runtime_objects_immutable_update
BEFORE UPDATE ON paper_runtime_objects
BEGIN
    SELECT RAISE(ABORT, 'paper runtime canonical objects are immutable');
END;

CREATE TRIGGER IF NOT EXISTS paper_runtime_objects_immutable_delete
BEFORE DELETE ON paper_runtime_objects
BEGIN
    SELECT RAISE(ABORT, 'paper runtime canonical objects are immutable');
END;

CREATE TABLE IF NOT EXISTS paper_position_lifecycle_projections (
    lifecycle_projection_id TEXT PRIMARY KEY,
    position_id TEXT NOT NULL,
    lifecycle_revision INTEGER NOT NULL CHECK (lifecycle_revision >= 0),
    previous_lifecycle_projection_id TEXT,
    lifecycle_projection_kind TEXT NOT NULL
        CHECK (lifecycle_projection_kind IN ('GENESIS', 'TRANSITION', 'REATTESTATION')),
    lifecycle_event TEXT,
    lifecycle_state TEXT NOT NULL,
    broker_state_observed_at TEXT NOT NULL,
    lifecycle_source_broker_state_observed_at TEXT NOT NULL,
    lifecycle_interpreted_at TEXT NOT NULL,
    broker_fact_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (position_id, lifecycle_revision)
);

CREATE INDEX IF NOT EXISTS paper_position_projection_position_idx
ON paper_position_lifecycle_projections(position_id, lifecycle_revision);

CREATE TRIGGER IF NOT EXISTS paper_position_projection_immutable_update
BEFORE UPDATE ON paper_position_lifecycle_projections
BEGIN
    SELECT RAISE(ABORT, 'paper Position lifecycle projection history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS paper_position_projection_immutable_delete
BEFORE DELETE ON paper_position_lifecycle_projections
BEGIN
    SELECT RAISE(ABORT, 'paper Position lifecycle projection history is append-only');
END;

CREATE TABLE IF NOT EXISTS paper_position_current_projection (
    position_id TEXT PRIMARY KEY,
    lifecycle_projection_id TEXT NOT NULL,
    lifecycle_revision INTEGER NOT NULL CHECK (lifecycle_revision >= 0),
    broker_state_observed_at TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    FOREIGN KEY (lifecycle_projection_id)
        REFERENCES paper_position_lifecycle_projections(lifecycle_projection_id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS paper_position_broker_observations (
    position_id TEXT NOT NULL,
    broker_state_observed_at TEXT NOT NULL,
    broker_fact_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (position_id, broker_state_observed_at)
);

CREATE INDEX IF NOT EXISTS paper_position_broker_observation_idx
ON paper_position_broker_observations(position_id, broker_state_observed_at);

CREATE TRIGGER IF NOT EXISTS paper_position_broker_observation_immutable_update
BEFORE UPDATE ON paper_position_broker_observations
BEGIN
    SELECT RAISE(ABORT, 'paper Position broker observation history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS paper_position_broker_observation_immutable_delete
BEFORE DELETE ON paper_position_broker_observations
BEGIN
    SELECT RAISE(ABORT, 'paper Position broker observation history is append-only');
END;

CREATE TABLE IF NOT EXISTS paper_order_result_observations (
    order_request_id TEXT NOT NULL,
    client_order_id TEXT NOT NULL,
    broker_order_id TEXT,
    observed_at TEXT NOT NULL,
    order_status TEXT NOT NULL,
    execution_health_status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (order_request_id, observed_at)
);

CREATE INDEX IF NOT EXISTS paper_order_result_client_idx
ON paper_order_result_observations(client_order_id, observed_at);

CREATE TRIGGER IF NOT EXISTS paper_order_result_observation_immutable_update
BEFORE UPDATE ON paper_order_result_observations
BEGIN
    SELECT RAISE(ABORT, 'paper OrderResult observation history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS paper_order_result_observation_immutable_delete
BEFORE DELETE ON paper_order_result_observations
BEGIN
    SELECT RAISE(ABORT, 'paper OrderResult observation history is append-only');
END;

CREATE TABLE IF NOT EXISTS paper_order_result_current (
    order_request_id TEXT PRIMARY KEY,
    observed_at TEXT NOT NULL,
    payload_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_funding_evidence (
    funding_evidence_id TEXT PRIMARY KEY,
    lineage_key_hash TEXT NOT NULL UNIQUE,
    trade_plan_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval_start TEXT NOT NULL,
    interval_end TEXT NOT NULL,
    interval_semantics TEXT NOT NULL,
    identity_material_hash TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS paper_funding_position_idx
ON paper_funding_evidence(position_id, interval_start, interval_end);

CREATE TRIGGER IF NOT EXISTS paper_funding_evidence_immutable_update
BEFORE UPDATE ON paper_funding_evidence
BEGIN
    SELECT RAISE(ABORT, 'canonical funding evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS paper_funding_evidence_immutable_delete
BEFORE DELETE ON paper_funding_evidence
BEGIN
    SELECT RAISE(ABORT, 'canonical funding evidence is immutable');
END;

CREATE TABLE IF NOT EXISTS paper_funding_observations (
    funding_evidence_id TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (funding_evidence_id, calculated_at),
    FOREIGN KEY (funding_evidence_id)
        REFERENCES paper_funding_evidence(funding_evidence_id)
        ON DELETE RESTRICT
);

CREATE TRIGGER IF NOT EXISTS paper_funding_observation_immutable_update
BEFORE UPDATE ON paper_funding_observations
BEGIN
    SELECT RAISE(ABORT, 'funding observation audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS paper_funding_observation_immutable_delete
BEFORE DELETE ON paper_funding_observations
BEGIN
    SELECT RAISE(ABORT, 'funding observation audit is append-only');
END;

CREATE TABLE IF NOT EXISTS paper_trade_results (
    trade_result_id TEXT PRIMARY KEY,
    trade_plan_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    funding_evidence_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (trade_plan_id, position_id),
    FOREIGN KEY (funding_evidence_id)
        REFERENCES paper_funding_evidence(funding_evidence_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS paper_trade_result_strategy_idx
ON paper_trade_results(strategy_id, strategy_version, trade_result_id);

CREATE TRIGGER IF NOT EXISTS paper_trade_result_immutable_update
BEFORE UPDATE ON paper_trade_results
BEGIN
    SELECT RAISE(ABORT, 'canonical TradeResult is immutable');
END;

CREATE TRIGGER IF NOT EXISTS paper_trade_result_immutable_delete
BEFORE DELETE ON paper_trade_results
BEGIN
    SELECT RAISE(ABORT, 'canonical TradeResult is immutable');
END;

CREATE TABLE IF NOT EXISTS paper_runtime_conflicts (
    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason_code TEXT NOT NULL,
    object_kind TEXT NOT NULL,
    canonical_id TEXT,
    trade_plan_id TEXT,
    position_id TEXT,
    existing_payload_hash TEXT,
    incoming_payload_hash TEXT,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS paper_runtime_conflict_position_idx
ON paper_runtime_conflicts(position_id, conflict_id);

CREATE INDEX IF NOT EXISTS paper_runtime_conflict_trade_plan_idx
ON paper_runtime_conflicts(trade_plan_id, conflict_id);

CREATE TRIGGER IF NOT EXISTS paper_runtime_conflict_immutable_update
BEFORE UPDATE ON paper_runtime_conflicts
BEGIN
    SELECT RAISE(ABORT, 'runtime conflict audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS paper_runtime_conflict_immutable_delete
BEFORE DELETE ON paper_runtime_conflicts
BEGIN
    SELECT RAISE(ABORT, 'runtime conflict audit is append-only');
END;
