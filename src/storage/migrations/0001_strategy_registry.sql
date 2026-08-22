PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS strategy_versions (
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    strategy_schema_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    declared_runtime_family TEXT NOT NULL,
    declared_runtime_version TEXT NOT NULL,
    definition_json TEXT NOT NULL,
    upstream_created_at TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    current_lifecycle_state TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (current_lifecycle_state IN ('DRAFT', 'BACKTESTING', 'REJECTED', 'CANDIDATE')),
    registry_revision INTEGER NOT NULL DEFAULT 0 CHECK (registry_revision >= 0),
    PRIMARY KEY (strategy_id, strategy_version)
);

CREATE TRIGGER IF NOT EXISTS strategy_versions_immutable_content
BEFORE UPDATE OF
    strategy_schema_version,
    content_hash,
    name,
    symbol,
    declared_runtime_family,
    declared_runtime_version,
    definition_json,
    upstream_created_at
ON strategy_versions
BEGIN
    SELECT RAISE(ABORT, 'strategy version content is immutable');
END;

CREATE TABLE IF NOT EXISTS compatibility_evidence (
    compatibility_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('PASS', 'FAIL', 'BLOCKED', 'NOT_RUN', 'NOT_APPLICABLE')),
    verification_kind TEXT NOT NULL
        CHECK (verification_kind IN ('LOCAL_EXECUTION', 'STATIC_REVIEW', 'DECLARATION', 'NOT_RUN')),
    checker TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    details_json TEXT NOT NULL,
    source_revision TEXT,
    environment TEXT,
    command TEXT,
    result_ref TEXT,
    FOREIGN KEY (strategy_id, strategy_version)
        REFERENCES strategy_versions(strategy_id, strategy_version)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS compatibility_evidence_strategy_idx
ON compatibility_evidence(strategy_id, strategy_version, checked_at);

CREATE TABLE IF NOT EXISTS validation_evidence (
    evidence_id TEXT PRIMARY KEY,
    evidence_type TEXT NOT NULL
        CHECK (evidence_type IN ('BACKTEST_RESULT', 'VALIDATION_DECISION')),
    upstream_object_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    strategy_content_hash TEXT NOT NULL,
    upstream_schema_version TEXT NOT NULL,
    producer TEXT NOT NULL,
    decision TEXT
        CHECK (decision IS NULL OR decision IN ('PASS', 'FAIL', 'BLOCKED', 'NOT_RUN')),
    parent_evidence_id TEXT,
    payload_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    verification_status TEXT NOT NULL
        CHECK (verification_status IN ('PASS', 'FAIL', 'BLOCKED', 'NOT_RUN', 'NOT_APPLICABLE')),
    verification_kind TEXT NOT NULL
        CHECK (verification_kind IN ('LOCAL_EXECUTION', 'STATIC_REVIEW', 'DECLARATION', 'NOT_RUN')),
    source_revision TEXT,
    environment TEXT,
    command TEXT,
    result_ref TEXT,
    UNIQUE (evidence_type, upstream_object_id),
    FOREIGN KEY (strategy_id, strategy_version)
        REFERENCES strategy_versions(strategy_id, strategy_version)
        ON DELETE RESTRICT,
    FOREIGN KEY (parent_evidence_id)
        REFERENCES validation_evidence(evidence_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS validation_evidence_strategy_idx
ON validation_evidence(strategy_id, strategy_version, evidence_type, recorded_at);

CREATE TABLE IF NOT EXISTS strategy_intake_receipts (
    intake_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    received_at TEXT NOT NULL,
    source_actor TEXT NOT NULL,
    result_status TEXT NOT NULL
        CHECK (result_status IN (
            'REGISTERED',
            'IDEMPOTENT',
            'COMPATIBILITY_FAIL',
            'COMPATIBILITY_BLOCKED',
            'COMPATIBILITY_NOT_RUN'
        )),
    compatibility_id TEXT,
    FOREIGN KEY (strategy_id, strategy_version)
        REFERENCES strategy_versions(strategy_id, strategy_version)
        ON DELETE RESTRICT,
    FOREIGN KEY (compatibility_id)
        REFERENCES compatibility_evidence(compatibility_id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS lifecycle_transitions (
    transition_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    previous_state TEXT NOT NULL
        CHECK (previous_state IN ('DRAFT', 'BACKTESTING', 'REJECTED', 'CANDIDATE')),
    new_state TEXT NOT NULL
        CHECK (new_state IN ('DRAFT', 'BACKTESTING', 'REJECTED', 'CANDIDATE')),
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    primary_evidence_id TEXT,
    expected_registry_revision INTEGER NOT NULL CHECK (expected_registry_revision >= 0),
    resulting_registry_revision INTEGER NOT NULL CHECK (resulting_registry_revision > 0),
    FOREIGN KEY (strategy_id, strategy_version)
        REFERENCES strategy_versions(strategy_id, strategy_version)
        ON DELETE RESTRICT,
    FOREIGN KEY (primary_evidence_id)
        REFERENCES validation_evidence(evidence_id)
        ON DELETE RESTRICT
);

CREATE TRIGGER IF NOT EXISTS lifecycle_transitions_allowed_edge_insert
BEFORE INSERT ON lifecycle_transitions
WHEN NOT (
    (NEW.previous_state = 'DRAFT' AND NEW.new_state = 'BACKTESTING') OR
    (NEW.previous_state = 'BACKTESTING' AND NEW.new_state = 'REJECTED') OR
    (NEW.previous_state = 'BACKTESTING' AND NEW.new_state = 'CANDIDATE')
)
BEGIN
    SELECT RAISE(ABORT, 'forbidden early Slice 2 lifecycle transition');
END;

CREATE INDEX IF NOT EXISTS lifecycle_transitions_strategy_idx
ON lifecycle_transitions(strategy_id, strategy_version, changed_at);

CREATE TRIGGER IF NOT EXISTS lifecycle_transitions_append_only_update
BEFORE UPDATE ON lifecycle_transitions
BEGIN
    SELECT RAISE(ABORT, 'lifecycle transition history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS lifecycle_transitions_append_only_delete
BEFORE DELETE ON lifecycle_transitions
BEGIN
    SELECT RAISE(ABORT, 'lifecycle transition history is append-only');
END;
