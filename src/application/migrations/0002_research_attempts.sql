CREATE TABLE IF NOT EXISTS research_runs (
    run_id TEXT PRIMARY KEY, input_json TEXT NOT NULL, input_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS research_runs_immutable BEFORE UPDATE ON research_runs
BEGIN SELECT RAISE(ABORT,'research inputs are immutable'); END;
CREATE TRIGGER IF NOT EXISTS research_runs_no_delete BEFORE DELETE ON research_runs
BEGIN SELECT RAISE(ABORT,'research inputs cannot be deleted'); END;
CREATE TABLE IF NOT EXISTS research_attempts (
    attempt_id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, stage TEXT NOT NULL,
    input_hash TEXT NOT NULL, owner_id TEXT NOT NULL, lease_generation INTEGER NOT NULL,
    lease_deadline TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','ABORTED','COMPLETE','FAILED')),
    output_json TEXT, output_hash TEXT, reason_codes_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(run_id,stage,lease_generation)
);
CREATE TRIGGER IF NOT EXISTS research_completed_immutable BEFORE UPDATE ON research_attempts
WHEN OLD.status!='RUNNING'
BEGIN SELECT RAISE(ABORT,'completed attempts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS research_attempt_inputs_immutable
BEFORE UPDATE OF run_id,stage,input_hash,owner_id,lease_generation,started_at ON research_attempts
BEGIN SELECT RAISE(ABORT,'attempt inputs are immutable'); END;
CREATE TRIGGER IF NOT EXISTS research_attempts_no_delete BEFORE DELETE ON research_attempts
BEGIN SELECT RAISE(ABORT,'research attempts cannot be deleted'); END;
