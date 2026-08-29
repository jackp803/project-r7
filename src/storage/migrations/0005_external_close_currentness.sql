PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS external_provider_ownership_evidence (
    ownership_evidence_id TEXT PRIMARY KEY,
    provider_object_class TEXT NOT NULL,
    provider_identity_ref TEXT NOT NULL,
    provider_object_ref TEXT NOT NULL,
    provider_snapshot_ref TEXT NOT NULL,
    provider_snapshot_hash TEXT NOT NULL,
    provider_observation_generation_id TEXT NOT NULL,
    supersedes_ownership_evidence_id TEXT,
    current_project_revision TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS external_provider_ownership_lineage_idx
ON external_provider_ownership_evidence(
    provider_object_class,
    provider_identity_ref,
    provider_object_ref,
    ownership_evidence_id
);

CREATE INDEX IF NOT EXISTS external_provider_ownership_supersedes_idx
ON external_provider_ownership_evidence(supersedes_ownership_evidence_id);

CREATE TRIGGER IF NOT EXISTS external_provider_ownership_immutable_update
BEFORE UPDATE ON external_provider_ownership_evidence
BEGIN
    SELECT RAISE(ABORT, 'external provider ownership evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS external_provider_ownership_immutable_delete
BEFORE DELETE ON external_provider_ownership_evidence
BEGIN
    SELECT RAISE(ABORT, 'external provider ownership evidence is immutable');
END;

CREATE TABLE IF NOT EXISTS external_manual_close_convergence_evidence (
    close_convergence_evidence_id TEXT PRIMARY KEY,
    position_id TEXT NOT NULL,
    provider_position_observation_generation_id TEXT NOT NULL,
    provider_position_snapshot_ref TEXT NOT NULL,
    provider_position_snapshot_hash TEXT NOT NULL,
    lifecycle_projection_id TEXT NOT NULL,
    lifecycle_revision INTEGER NOT NULL CHECK (lifecycle_revision >= 0),
    lifecycle_projection_hash TEXT NOT NULL,
    lifecycle_execution_binding_ref TEXT NOT NULL,
    lifecycle_execution_binding_hash TEXT NOT NULL,
    execution_evidence_set_hash TEXT NOT NULL,
    fp04_evidence_set_hash TEXT NOT NULL,
    terminal_protection_observation_ref TEXT NOT NULL,
    terminal_protection_observation_hash TEXT NOT NULL,
    convergence_state TEXT NOT NULL,
    supersedes_close_convergence_evidence_id TEXT,
    evaluated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS external_close_convergence_position_idx
ON external_manual_close_convergence_evidence(position_id, close_convergence_evidence_id);

CREATE INDEX IF NOT EXISTS external_close_convergence_generation_idx
ON external_manual_close_convergence_evidence(
    position_id,
    provider_position_observation_generation_id,
    close_convergence_evidence_id
);

CREATE INDEX IF NOT EXISTS external_close_convergence_supersedes_idx
ON external_manual_close_convergence_evidence(supersedes_close_convergence_evidence_id);

CREATE TRIGGER IF NOT EXISTS external_close_convergence_immutable_update
BEFORE UPDATE ON external_manual_close_convergence_evidence
BEGIN
    SELECT RAISE(ABORT, 'external manual close convergence evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS external_close_convergence_immutable_delete
BEFORE DELETE ON external_manual_close_convergence_evidence
BEGIN
    SELECT RAISE(ABORT, 'external manual close convergence evidence is immutable');
END;

CREATE TABLE IF NOT EXISTS external_close_reinterpretation_decisions (
    decision_id TEXT PRIMARY KEY,
    position_id TEXT NOT NULL,
    close_convergence_evidence_id TEXT NOT NULL,
    close_convergence_evidence_hash TEXT NOT NULL,
    lifecycle_projection_ref TEXT NOT NULL,
    lifecycle_projection_id TEXT NOT NULL,
    lifecycle_revision INTEGER NOT NULL CHECK (lifecycle_revision >= 0),
    lifecycle_execution_binding_ref TEXT,
    lifecycle_execution_binding_id TEXT,
    decision TEXT NOT NULL,
    event TEXT,
    next_state TEXT NOT NULL,
    close_eligible INTEGER NOT NULL CHECK (close_eligible IN (0, 1)),
    trade_result_evidence_incomplete INTEGER NOT NULL CHECK (trade_result_evidence_incomplete IN (0, 1)),
    evidence_current INTEGER NOT NULL CHECK (evidence_current IN (0, 1)),
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS external_close_decision_position_idx
ON external_close_reinterpretation_decisions(position_id, decision_id);

CREATE INDEX IF NOT EXISTS external_close_decision_fp10_idx
ON external_close_reinterpretation_decisions(close_convergence_evidence_id, decision_id);

CREATE TRIGGER IF NOT EXISTS external_close_decision_immutable_update
BEFORE UPDATE ON external_close_reinterpretation_decisions
BEGIN
    SELECT RAISE(ABORT, 'external close reinterpretation decision is immutable');
END;

CREATE TRIGGER IF NOT EXISTS external_close_decision_immutable_delete
BEFORE DELETE ON external_close_reinterpretation_decisions
BEGIN
    SELECT RAISE(ABORT, 'external close reinterpretation decision is immutable');
END;

CREATE TABLE IF NOT EXISTS external_currentness_conflicts (
    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason_code TEXT NOT NULL,
    object_kind TEXT NOT NULL,
    canonical_id TEXT,
    position_id TEXT,
    existing_payload_hash TEXT,
    incoming_payload_hash TEXT,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS external_currentness_conflict_position_idx
ON external_currentness_conflicts(position_id, conflict_id);

CREATE TRIGGER IF NOT EXISTS external_currentness_conflict_immutable_update
BEFORE UPDATE ON external_currentness_conflicts
BEGIN
    SELECT RAISE(ABORT, 'external currentness conflict audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS external_currentness_conflict_immutable_delete
BEFORE DELETE ON external_currentness_conflicts
BEGIN
    SELECT RAISE(ABORT, 'external currentness conflict audit is append-only');
END;
