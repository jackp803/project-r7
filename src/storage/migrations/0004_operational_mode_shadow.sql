PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS operational_mode_transitions (
    transition_id TEXT PRIMARY KEY,
    mode_revision INTEGER NOT NULL UNIQUE CHECK (mode_revision >= 0),
    schema_version TEXT NOT NULL CHECK (schema_version = 'contracts-v0.1'),
    previous_mode TEXT
        CHECK (previous_mode IS NULL OR previous_mode IN ('RESEARCH', 'PAPER', 'SHADOW', 'LIVE', 'PAUSED', 'LOCKED')),
    new_mode TEXT NOT NULL
        CHECK (new_mode IN ('RESEARCH', 'PAPER', 'SHADOW', 'LIVE', 'PAUSED', 'LOCKED')),
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    approval_record_id TEXT,
    evidence_ref TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TRIGGER IF NOT EXISTS operational_mode_transition_immutable_update
BEFORE UPDATE ON operational_mode_transitions
BEGIN
    SELECT RAISE(ABORT, 'operational mode transition audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS operational_mode_transition_immutable_delete
BEFORE DELETE ON operational_mode_transitions
BEGIN
    SELECT RAISE(ABORT, 'operational mode transition audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS operational_mode_first_revision_guard
BEFORE INSERT ON operational_mode_transitions
WHEN NEW.mode_revision = 0
AND EXISTS (SELECT 1 FROM operational_mode_transitions)
BEGIN
    SELECT RAISE(ABORT, 'operational mode revision 0 already exists');
END;

CREATE TRIGGER IF NOT EXISTS operational_mode_chain_guard
BEFORE INSERT ON operational_mode_transitions
WHEN NEW.mode_revision > 0
AND NOT EXISTS (
    SELECT 1
    FROM operational_mode_transitions previous
    WHERE previous.mode_revision = NEW.mode_revision - 1
      AND previous.new_mode = NEW.previous_mode
)
BEGIN
    SELECT RAISE(ABORT, 'operational mode predecessor mismatch');
END;

CREATE TRIGGER IF NOT EXISTS operational_mode_live_transition_forbidden_gate_c
BEFORE INSERT ON operational_mode_transitions
WHEN NEW.mode_revision > 0 AND NEW.new_mode = 'LIVE'
BEGIN
    SELECT RAISE(ABORT, 'Gate C does not authorize transition into LIVE');
END;

CREATE TABLE IF NOT EXISTS shadow_provider_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    checkpoint_revision INTEGER NOT NULL UNIQUE CHECK (checkpoint_revision >= 0),
    mode_revision INTEGER NOT NULL,
    observed_at TEXT NOT NULL,
    provider_observation_ref TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (mode_revision)
        REFERENCES operational_mode_transitions(mode_revision)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS shadow_provider_checkpoint_mode_revision_idx
ON shadow_provider_checkpoints(mode_revision, checkpoint_revision);

CREATE TRIGGER IF NOT EXISTS shadow_provider_checkpoint_immutable_update
BEFORE UPDATE ON shadow_provider_checkpoints
BEGIN
    SELECT RAISE(ABORT, 'Shadow provider checkpoint audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS shadow_provider_checkpoint_immutable_delete
BEFORE DELETE ON shadow_provider_checkpoints
BEGIN
    SELECT RAISE(ABORT, 'Shadow provider checkpoint audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS shadow_provider_checkpoint_mode_guard
BEFORE INSERT ON shadow_provider_checkpoints
WHEN NOT EXISTS (
    SELECT 1
    FROM operational_mode_transitions mode_transition
    WHERE mode_transition.mode_revision = NEW.mode_revision
      AND mode_transition.new_mode = 'SHADOW'
)
BEGIN
    SELECT RAISE(ABORT, 'Shadow checkpoint requires SHADOW operational mode revision');
END;
