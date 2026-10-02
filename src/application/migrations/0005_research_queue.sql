CREATE TABLE IF NOT EXISTS research_queue_namespace(singleton INTEGER PRIMARY KEY CHECK(singleton=1),namespace TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_queue_jobs(
    run_id TEXT PRIMARY KEY,submission_id TEXT NOT NULL,policy_id TEXT NOT NULL,
    input_json TEXT NOT NULL,input_hash TEXT NOT NULL,implementation_hash TEXT NOT NULL,
    state TEXT NOT NULL,revision INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
    owner_id TEXT,generation INTEGER NOT NULL DEFAULT 0,lease_deadline TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0,owner_run_id TEXT,stage TEXT,
    outcome_json TEXT,reason_codes_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS research_queue_commands(command_id TEXT PRIMARY KEY,request_json TEXT NOT NULL,receipt_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_queue_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL,
    state TEXT NOT NULL,generation INTEGER NOT NULL,revision INTEGER NOT NULL,observed_at TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS research_queue_input_immutable BEFORE UPDATE ON research_queue_jobs
    WHEN NEW.input_json<>OLD.input_json OR NEW.input_hash<>OLD.input_hash OR NEW.implementation_hash<>OLD.implementation_hash
    OR NEW.submission_id<>OLD.submission_id OR NEW.policy_id<>OLD.policy_id OR NEW.run_id<>OLD.run_id OR NEW.created_at<>OLD.created_at
    BEGIN SELECT RAISE(ABORT,'Queued subject is immutable'); END;
CREATE TRIGGER IF NOT EXISTS research_queue_no_delete BEFORE DELETE ON research_queue_jobs
    BEGIN SELECT RAISE(ABORT,'Queued evidence is retained'); END;
CREATE TRIGGER IF NOT EXISTS research_queue_command_immutable BEFORE UPDATE ON research_queue_commands
    BEGIN SELECT RAISE(ABORT,'Queue command receipt is immutable'); END;
CREATE TRIGGER IF NOT EXISTS research_queue_command_no_delete BEFORE DELETE ON research_queue_commands
    BEGIN SELECT RAISE(ABORT,'Queue command receipt is retained'); END;
