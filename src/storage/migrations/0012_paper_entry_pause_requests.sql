-- r7-migration-transaction: atomic
CREATE TABLE paper_entry_pause_requests(
 command_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES paper_process_runs(run_id),
 request_json TEXT NOT NULL,request_hash TEXT NOT NULL,receipt_json TEXT NOT NULL,receipt_hash TEXT NOT NULL,
 requested_at TEXT NOT NULL
);
CREATE INDEX paper_entry_pause_run ON paper_entry_pause_requests(run_id,requested_at,command_id);
CREATE TRIGGER paper_entry_pause_no_update BEFORE UPDATE ON paper_entry_pause_requests
BEGIN SELECT RAISE(ABORT,'Entry pause requests are immutable'); END;
CREATE TRIGGER paper_entry_pause_no_delete BEFORE DELETE ON paper_entry_pause_requests
BEGIN SELECT RAISE(ABORT,'Entry pause requests are retained'); END;
