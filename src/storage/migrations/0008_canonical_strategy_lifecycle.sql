-- r7-migration-transaction: foreign-key-rebuild

-- Owner migration runner supplies BEGIN/foreign-key verification/receipt/COMMIT.

-- Copy before drop; no changes to identities, definitions, evidence or history.

DROP TRIGGER IF EXISTS strategy_versions_lifecycle_projection_guard;

CREATE TABLE strategy_versions_v02 (
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
        CHECK (current_lifecycle_state IN ('DRAFT', 'BACKTESTING', 'REJECTED', 'CANDIDATE', 'PAPER', 'READY_FOR_APPROVAL', 'APPROVED', 'LIVE', 'DEGRADED', 'RETIRED')),
    registry_revision INTEGER NOT NULL DEFAULT 0 CHECK (registry_revision >= 0),
    PRIMARY KEY (strategy_id, strategy_version)
);

CREATE TABLE lifecycle_transitions_v02 (
    transition_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    previous_state TEXT NOT NULL
        CHECK (previous_state IN ('DRAFT', 'BACKTESTING', 'REJECTED', 'CANDIDATE', 'PAPER', 'READY_FOR_APPROVAL', 'APPROVED', 'LIVE', 'DEGRADED', 'RETIRED')),
    new_state TEXT NOT NULL
        CHECK (new_state IN ('DRAFT', 'BACKTESTING', 'REJECTED', 'CANDIDATE', 'PAPER', 'READY_FOR_APPROVAL', 'APPROVED', 'LIVE', 'DEGRADED', 'RETIRED')),
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

INSERT INTO strategy_versions_v02 SELECT * FROM strategy_versions;

INSERT INTO lifecycle_transitions_v02 SELECT * FROM lifecycle_transitions;

DROP TABLE lifecycle_transitions;

DROP TABLE strategy_versions;

ALTER TABLE strategy_versions_v02 RENAME TO strategy_versions;

ALTER TABLE lifecycle_transitions_v02 RENAME TO lifecycle_transitions;

CREATE TRIGGER IF NOT EXISTS strategy_versions_initial_projection_guard
BEFORE INSERT ON strategy_versions
WHEN NEW.current_lifecycle_state <> 'DRAFT' OR NEW.registry_revision <> 0
BEGIN
    SELECT RAISE(ABORT, 'new strategy projection must start at DRAFT revision 0');
END;

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

CREATE TRIGGER IF NOT EXISTS lifecycle_transitions_allowed_edge_insert
BEFORE INSERT ON lifecycle_transitions
WHEN NOT (
    (NEW.previous_state = 'DRAFT' AND NEW.new_state = 'BACKTESTING') OR
    (NEW.previous_state = 'DRAFT' AND NEW.new_state = 'RETIRED') OR
    (NEW.previous_state = 'BACKTESTING' AND NEW.new_state = 'REJECTED') OR
    (NEW.previous_state = 'BACKTESTING' AND NEW.new_state = 'CANDIDATE') OR
    (NEW.previous_state = 'CANDIDATE' AND NEW.new_state = 'PAPER') OR
    (NEW.previous_state = 'CANDIDATE' AND NEW.new_state = 'REJECTED') OR
    (NEW.previous_state = 'CANDIDATE' AND NEW.new_state = 'RETIRED') OR
    (NEW.previous_state = 'PAPER' AND NEW.new_state = 'READY_FOR_APPROVAL') OR
    (NEW.previous_state = 'PAPER' AND NEW.new_state = 'REJECTED') OR
    (NEW.previous_state = 'PAPER' AND NEW.new_state = 'RETIRED') OR
    (NEW.previous_state = 'READY_FOR_APPROVAL' AND NEW.new_state = 'APPROVED') OR
    (NEW.previous_state = 'READY_FOR_APPROVAL' AND NEW.new_state = 'REJECTED') OR
    (NEW.previous_state = 'READY_FOR_APPROVAL' AND NEW.new_state = 'RETIRED') OR
    (NEW.previous_state = 'APPROVED' AND NEW.new_state = 'LIVE') OR
    (NEW.previous_state = 'APPROVED' AND NEW.new_state = 'RETIRED') OR
    (NEW.previous_state = 'LIVE' AND NEW.new_state = 'DEGRADED') OR
    (NEW.previous_state = 'LIVE' AND NEW.new_state = 'RETIRED') OR
    (NEW.previous_state = 'DEGRADED' AND NEW.new_state = 'LIVE') OR
    (NEW.previous_state = 'DEGRADED' AND NEW.new_state = 'RETIRED')
)
BEGIN
    SELECT RAISE(ABORT, 'forbidden canonical lifecycle transition');
END;

CREATE TRIGGER IF NOT EXISTS strategy_versions_lifecycle_projection_guard
BEFORE UPDATE OF current_lifecycle_state, registry_revision ON strategy_versions
WHEN NOT (
    NEW.registry_revision = OLD.registry_revision + 1
    AND EXISTS (
        SELECT 1
        FROM lifecycle_transitions AS transition
        WHERE transition.strategy_id = OLD.strategy_id
          AND transition.strategy_version = OLD.strategy_version
          AND transition.previous_state = OLD.current_lifecycle_state
          AND transition.new_state = NEW.current_lifecycle_state
          AND transition.expected_registry_revision = OLD.registry_revision
          AND transition.resulting_registry_revision = NEW.registry_revision
    )
)
BEGIN
    SELECT RAISE(ABORT, 'lifecycle projection update requires matching transition history');
END;

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

CREATE INDEX IF NOT EXISTS lifecycle_transitions_strategy_idx ON lifecycle_transitions(strategy_id,strategy_version,changed_at);
