CREATE TABLE IF NOT EXISTS app_submissions (
    instance_id TEXT NOT NULL, submission_id TEXT NOT NULL, manifest_hash TEXT NOT NULL,
    owner_id TEXT NOT NULL, lease_generation INTEGER NOT NULL CHECK(lease_generation>0),
    lease_deadline TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>=0),
    state TEXT NOT NULL CHECK(state IN ('CLAIMED','INTAKE_ACCEPTED')), effect_ref TEXT,
    PRIMARY KEY(instance_id,submission_id)
);
CREATE TABLE IF NOT EXISTS app_outbox (
    operation_id TEXT PRIMARY KEY, instance_id TEXT NOT NULL, submission_id TEXT NOT NULL,
    logical_path TEXT NOT NULL UNIQUE, payload BLOB NOT NULL, payload_hash TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('PENDING','LOCAL_STAGED','CLOUD_ACKNOWLEDGED','UNAVAILABLE','CONFLICT')),
    artifact_hash TEXT, attempts INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(instance_id,submission_id) REFERENCES app_submissions(instance_id,submission_id)
);
CREATE TRIGGER IF NOT EXISTS app_outbox_immutable
BEFORE UPDATE OF operation_id,instance_id,submission_id,logical_path,payload,payload_hash ON app_outbox
BEGIN SELECT RAISE(ABORT, 'outbox content is immutable'); END;
CREATE TRIGGER IF NOT EXISTS app_outbox_no_delete
BEFORE DELETE ON app_outbox
BEGIN SELECT RAISE(ABORT, 'outbox evidence cannot be deleted'); END;
CREATE TABLE IF NOT EXISTS app_submission_observations (
    observation_id INTEGER PRIMARY KEY, instance_id TEXT NOT NULL, submission_id TEXT NOT NULL,
    state TEXT NOT NULL, reason TEXT NOT NULL, observed_at TEXT NOT NULL, manifest_hash TEXT
);
CREATE TABLE IF NOT EXISTS app_sync_retry (
    instance_id TEXT NOT NULL,submission_id TEXT NOT NULL,manifest_hash TEXT,
    first_observed_at TEXT NOT NULL,attempts INTEGER NOT NULL,next_retry_at TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('INCOMPLETE_SYNC','SYNC_STALLED')),
    PRIMARY KEY(instance_id,submission_id)
);
