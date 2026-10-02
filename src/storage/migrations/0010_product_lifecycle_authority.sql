-- r7-migration-transaction: atomic
CREATE TABLE lifecycle_owner_evidence (
 evidence_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
 strategy_id TEXT NOT NULL, strategy_version TEXT NOT NULL,
 strategy_content_hash TEXT NOT NULL, namespace TEXT NOT NULL,
 release_json TEXT NOT NULL, release_hash TEXT NOT NULL,
 actor TEXT NOT NULL, command_id TEXT NOT NULL UNIQUE, expected_revision INTEGER NOT NULL,
 payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL,
 issued_at TEXT NOT NULL, expires_at TEXT NOT NULL,
 FOREIGN KEY(strategy_id,strategy_version) REFERENCES strategy_versions(strategy_id,strategy_version)
);
CREATE TABLE human_approvals (
 approval_record_id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL, strategy_version TEXT NOT NULL,
 namespace TEXT NOT NULL, actor TEXT NOT NULL, command_id TEXT NOT NULL UNIQUE,
 expected_revision INTEGER NOT NULL, envelope_json TEXT NOT NULL, envelope_hash TEXT NOT NULL,
 payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL, recorded_at TEXT NOT NULL,
 FOREIGN KEY(strategy_id,strategy_version) REFERENCES strategy_versions(strategy_id,strategy_version)
);
CREATE TABLE approval_revocations (
 revocation_id TEXT PRIMARY KEY, approval_record_id TEXT NOT NULL REFERENCES human_approvals(approval_record_id),
 actor TEXT NOT NULL, reason TEXT NOT NULL, command_id TEXT NOT NULL UNIQUE, recorded_at TEXT NOT NULL
);
CREATE TABLE lifecycle_command_receipts (
 command_id TEXT PRIMARY KEY, request_json TEXT NOT NULL, request_hash TEXT NOT NULL,
 output_json TEXT NOT NULL, output_hash TEXT NOT NULL,
 transition_id TEXT NOT NULL REFERENCES lifecycle_transitions(transition_id), recorded_at TEXT NOT NULL
);
ALTER TABLE lifecycle_transitions ADD COLUMN owner_evidence_id TEXT REFERENCES lifecycle_owner_evidence(evidence_id);
CREATE TRIGGER lifecycle_owner_evidence_no_update BEFORE UPDATE ON lifecycle_owner_evidence
BEGIN SELECT RAISE(ABORT,'owner evidence is immutable'); END;
CREATE TRIGGER lifecycle_owner_evidence_no_delete BEFORE DELETE ON lifecycle_owner_evidence
BEGIN SELECT RAISE(ABORT,'owner evidence cannot be deleted'); END;
CREATE TRIGGER human_approvals_no_update BEFORE UPDATE ON human_approvals
BEGIN SELECT RAISE(ABORT,'human approvals are immutable'); END;
CREATE TRIGGER human_approvals_no_delete BEFORE DELETE ON human_approvals
BEGIN SELECT RAISE(ABORT,'human approvals cannot be deleted'); END;
CREATE TRIGGER approval_revocations_no_update BEFORE UPDATE ON approval_revocations
BEGIN SELECT RAISE(ABORT,'revocations are immutable'); END;
CREATE TRIGGER approval_revocations_no_delete BEFORE DELETE ON approval_revocations
BEGIN SELECT RAISE(ABORT,'revocations cannot be deleted'); END;
CREATE TRIGGER lifecycle_command_receipts_no_update BEFORE UPDATE ON lifecycle_command_receipts
BEGIN SELECT RAISE(ABORT,'lifecycle command receipts are immutable'); END;
CREATE TRIGGER lifecycle_command_receipts_no_delete BEFORE DELETE ON lifecycle_command_receipts
BEGIN SELECT RAISE(ABORT,'lifecycle command receipts cannot be deleted'); END;
