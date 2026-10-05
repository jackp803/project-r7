CREATE TABLE IF NOT EXISTS research_feedback_publications (
    operation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES research_runs(run_id),
    feedback_json TEXT NOT NULL,
    feedback_hash TEXT NOT NULL,
    logical_path TEXT NOT NULL UNIQUE,
    payloads_json TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('PENDING','LOCAL_STAGED','CLOUD_ACKNOWLEDGED','UNAVAILABLE','CONFLICT')),
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS research_feedback_publications_immutable
BEFORE UPDATE OF operation_id,run_id,feedback_json,feedback_hash,logical_path,payloads_json,artifact_hash,created_at
ON research_feedback_publications
BEGIN SELECT RAISE(ABORT, 'feedback publication content is immutable'); END;
CREATE TRIGGER IF NOT EXISTS research_feedback_publications_no_delete
BEFORE DELETE ON research_feedback_publications
BEGIN SELECT RAISE(ABORT, 'feedback publication evidence cannot be deleted'); END;
