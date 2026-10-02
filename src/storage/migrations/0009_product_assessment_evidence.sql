-- r7-migration-transaction: atomic
CREATE TABLE product_assessments (
    assessment_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    strategy_content_hash TEXT NOT NULL,
    namespace TEXT NOT NULL CHECK(namespace IN ('FIXTURE','LOCAL_RESEARCH')),
    implementation_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PASS','FAIL','BLOCKED')),
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    risk_policy_json TEXT,
    risk_policy_hash TEXT,
    validation_evidence_id TEXT REFERENCES validation_evidence(evidence_id),
    recorded_at TEXT NOT NULL,
    result_ref TEXT NOT NULL,
    FOREIGN KEY(strategy_id,strategy_version) REFERENCES strategy_versions(strategy_id,strategy_version)
);
CREATE INDEX product_assessments_subject ON product_assessments(strategy_id,strategy_version);
CREATE TRIGGER product_assessment_no_update BEFORE UPDATE ON product_assessments
BEGIN SELECT RAISE(ABORT,'product assessments are immutable'); END;
CREATE TRIGGER product_assessment_no_delete BEFORE DELETE ON product_assessments
BEGIN SELECT RAISE(ABORT,'product assessments cannot be deleted'); END;
