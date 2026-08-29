PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS protection_registry_multiplicity_evidence (
    protection_registry_evidence_id TEXT PRIMARY KEY,
    position_id TEXT NOT NULL,
    position_ref TEXT NOT NULL,
    position_hash TEXT NOT NULL,
    position_observed_at TEXT NOT NULL,
    position_action_id TEXT NOT NULL,
    approved_trade_plan_ref TEXT NOT NULL,
    protection_order_request_ref TEXT,
    client_order_identity_ref TEXT,
    lineage_key_hash TEXT NOT NULL,
    intended_protection_lineage_hash TEXT NOT NULL,
    provider_identity_ref TEXT NOT NULL,
    provider_instrument_ref TEXT NOT NULL,
    provider_observation_generation_id TEXT NOT NULL,
    provider_observed_at TEXT NOT NULL,
    provider_received_at TEXT NOT NULL,
    observation_coverage_status TEXT NOT NULL,
    provider_set_currentness_status TEXT NOT NULL,
    observed_active_protection_set_hash TEXT NOT NULL,
    lifecycle_projection_ref TEXT,
    lifecycle_execution_binding_ref TEXT,
    runtime_preflight_ref TEXT,
    runtime_process_instance_id TEXT,
    runtime_process_start_generation_id TEXT,
    runtime_config_generation_id TEXT,
    multiplicity_state TEXT NOT NULL,
    registry_status TEXT NOT NULL,
    supersedes_registry_evidence_id TEXT,
    evaluated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS protection_registry_lineage_idx
ON protection_registry_multiplicity_evidence(
    position_id,
    lineage_key_hash,
    protection_registry_evidence_id
);

CREATE INDEX IF NOT EXISTS protection_registry_position_action_idx
ON protection_registry_multiplicity_evidence(
    position_id,
    position_action_id,
    protection_registry_evidence_id
);

CREATE INDEX IF NOT EXISTS protection_registry_supersedes_idx
ON protection_registry_multiplicity_evidence(supersedes_registry_evidence_id);

CREATE INDEX IF NOT EXISTS protection_registry_provider_generation_idx
ON protection_registry_multiplicity_evidence(
    provider_identity_ref,
    provider_instrument_ref,
    provider_observation_generation_id,
    protection_registry_evidence_id
);

CREATE TRIGGER IF NOT EXISTS protection_registry_evidence_immutable_update
BEFORE UPDATE ON protection_registry_multiplicity_evidence
BEGIN
    SELECT RAISE(ABORT, 'protection registry multiplicity evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS protection_registry_evidence_immutable_delete
BEFORE DELETE ON protection_registry_multiplicity_evidence
BEGIN
    SELECT RAISE(ABORT, 'protection registry multiplicity evidence is immutable');
END;

CREATE TABLE IF NOT EXISTS protection_registry_policy_interpretations (
    decision_id TEXT NOT NULL,
    source_registry_evidence_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    position_ref TEXT NOT NULL,
    position_hash TEXT NOT NULL,
    position_observed_at TEXT NOT NULL,
    lifecycle_projection_id TEXT NOT NULL,
    lifecycle_revision INTEGER NOT NULL CHECK (lifecycle_revision >= 0),
    lifecycle_execution_binding_id TEXT,
    source_registry_evidence_hash TEXT NOT NULL,
    source_registry_material_hash TEXT NOT NULL,
    decision TEXT NOT NULL,
    event TEXT,
    next_state TEXT NOT NULL,
    healthy_protection INTEGER NOT NULL CHECK (healthy_protection IN (0, 1)),
    terminal_close_dependency INTEGER NOT NULL CHECK (terminal_close_dependency IN (0, 1)),
    provider_mutation_authorized INTEGER NOT NULL CHECK (provider_mutation_authorized IN (0, 1)),
    cleanup_target_ref TEXT,
    evidence_current INTEGER NOT NULL CHECK (evidence_current IN (0, 1)),
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (decision_id, source_registry_evidence_id),
    FOREIGN KEY (source_registry_evidence_id)
        REFERENCES protection_registry_multiplicity_evidence(protection_registry_evidence_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS protection_registry_policy_position_idx
ON protection_registry_policy_interpretations(position_id, source_registry_evidence_id, decision_id);

CREATE INDEX IF NOT EXISTS protection_registry_policy_source_idx
ON protection_registry_policy_interpretations(source_registry_evidence_id, decision_id);

CREATE TRIGGER IF NOT EXISTS protection_registry_policy_interpretation_immutable_update
BEFORE UPDATE ON protection_registry_policy_interpretations
BEGIN
    SELECT RAISE(ABORT, 'protection registry policy interpretation is immutable');
END;

CREATE TRIGGER IF NOT EXISTS protection_registry_policy_interpretation_immutable_delete
BEFORE DELETE ON protection_registry_policy_interpretations
BEGIN
    SELECT RAISE(ABORT, 'protection registry policy interpretation is immutable');
END;
