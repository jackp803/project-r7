-- r7-migration-transaction: atomic
CREATE TABLE paper_process_storage_profiles (
 run_id TEXT PRIMARY KEY REFERENCES paper_process_runs(run_id),
 profile TEXT NOT NULL CHECK(profile='r7-paper-state-zlib-delta-v0.1'),
 created_at TEXT NOT NULL
);
CREATE TRIGGER paper_process_storage_profiles_no_update BEFORE UPDATE ON paper_process_storage_profiles
BEGIN SELECT RAISE(ABORT,'Paper storage profile is immutable'); END;
CREATE TRIGGER paper_process_storage_profiles_no_delete BEFORE DELETE ON paper_process_storage_profiles
BEGIN SELECT RAISE(ABORT,'Paper storage profile is immutable'); END;
CREATE TRIGGER paper_process_storage_profiles_no_reselect BEFORE INSERT ON paper_process_storage_profiles
WHEN EXISTS(SELECT 1 FROM paper_process_storage_profiles WHERE run_id=NEW.run_id)
 OR EXISTS(SELECT 1 FROM paper_process_checkpoints WHERE run_id=NEW.run_id)
BEGIN SELECT RAISE(ABORT,'Paper storage profile requires a new run'); END;
