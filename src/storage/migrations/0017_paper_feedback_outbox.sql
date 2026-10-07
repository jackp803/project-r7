-- r7-migration-transaction: atomic
CREATE TABLE paper_feedback_publications (
 operation_id TEXT PRIMARY KEY,
 run_id TEXT NOT NULL REFERENCES paper_process_runs(run_id),
 run_revision INTEGER NOT NULL CHECK(run_revision>=0),
 process_generation INTEGER NOT NULL CHECK(process_generation>0),
 binding_hash TEXT NOT NULL,
 checkpoint_state_hash TEXT NOT NULL,
 feedback_json TEXT NOT NULL,
 feedback_hash TEXT NOT NULL,
 logical_path TEXT NOT NULL,
 payloads_json TEXT NOT NULL,
 artifact_hash TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('PENDING','LOCAL_STAGED','CLOUD_ACKNOWLEDGED','UNAVAILABLE','CONFLICT')),
 attempts INTEGER NOT NULL CHECK(attempts>=0),
 created_at TEXT NOT NULL,
 FOREIGN KEY(run_id,run_revision) REFERENCES paper_process_checkpoints(run_id,revision),
 FOREIGN KEY(run_id,process_generation) REFERENCES paper_process_generations(run_id,generation)
);
CREATE INDEX paper_feedback_pending ON paper_feedback_publications(state,operation_id);
