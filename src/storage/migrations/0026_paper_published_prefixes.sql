-- r7-migration-transaction: atomic
CREATE TABLE paper_process_prefix_profiles (
 run_id TEXT PRIMARY KEY REFERENCES paper_process_storage_profiles(run_id),
 profile TEXT NOT NULL CHECK(profile='r7-paper-published-prefix-v0.1'),
 created_at TEXT NOT NULL
);
CREATE TRIGGER paper_process_prefix_profiles_no_update BEFORE UPDATE ON paper_process_prefix_profiles
BEGIN SELECT RAISE(ABORT,'Paper prefix profile is immutable'); END;
CREATE TRIGGER paper_process_prefix_profiles_no_delete BEFORE DELETE ON paper_process_prefix_profiles
BEGIN SELECT RAISE(ABORT,'Paper prefix profile is immutable'); END;
CREATE TRIGGER paper_process_prefix_profiles_no_reselect BEFORE INSERT ON paper_process_prefix_profiles
WHEN EXISTS(SELECT 1 FROM paper_process_prefix_profiles WHERE run_id=NEW.run_id)
 OR EXISTS(SELECT 1 FROM paper_process_checkpoints WHERE run_id=NEW.run_id)
BEGIN SELECT RAISE(ABORT,'Paper prefix profile requires a new run'); END;
CREATE TABLE paper_process_published_prefixes (
 run_id TEXT NOT NULL REFERENCES paper_process_prefix_profiles(run_id),
 revision INTEGER NOT NULL CHECK(revision>=0), operation_id TEXT,
 previous_hash TEXT NOT NULL, prefix_hash TEXT NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(run_id,revision), UNIQUE(run_id,operation_id),
 FOREIGN KEY(run_id,revision) REFERENCES paper_process_checkpoints(run_id,revision),
 FOREIGN KEY(run_id,operation_id) REFERENCES paper_process_publications(run_id,operation_id),
 CHECK((revision=0 AND operation_id IS NULL) OR (revision>0 AND operation_id IS NOT NULL))
);
CREATE TRIGGER paper_process_published_prefixes_no_update BEFORE UPDATE ON paper_process_published_prefixes
BEGIN SELECT RAISE(ABORT,'Paper published prefix is immutable'); END;
CREATE TRIGGER paper_process_published_prefixes_no_delete BEFORE DELETE ON paper_process_published_prefixes
BEGIN SELECT RAISE(ABORT,'Paper published prefix is immutable'); END;
CREATE TRIGGER paper_process_published_prefixes_no_replace BEFORE INSERT ON paper_process_published_prefixes
WHEN EXISTS(SELECT 1 FROM paper_process_published_prefixes WHERE run_id=NEW.run_id AND (revision=NEW.revision OR operation_id=NEW.operation_id))
BEGIN SELECT RAISE(ABORT,'Paper published prefix replacement is forbidden'); END;
CREATE TRIGGER paper_process_published_prefixes_predecessor BEFORE INSERT ON paper_process_published_prefixes
WHEN NEW.revision>0 AND NOT EXISTS(SELECT 1 FROM paper_process_published_prefixes
 WHERE run_id=NEW.run_id AND revision=NEW.revision-1 AND prefix_hash=NEW.previous_hash)
BEGIN SELECT RAISE(ABORT,'Paper published prefix predecessor required'); END;
CREATE TRIGGER paper_process_published_prefixes_source BEFORE INSERT ON paper_process_published_prefixes
WHEN NEW.revision>0 AND NOT EXISTS(
 SELECT 1 FROM paper_process_publications p
 JOIN paper_process_effects e USING(run_id,operation_id)
 JOIN paper_process_operations o USING(run_id,operation_id)
 JOIN paper_process_checkpoints c ON c.run_id=e.run_id AND c.revision=e.checkpoint_revision
 WHERE p.run_id=NEW.run_id AND p.operation_id=NEW.operation_id
 AND e.checkpoint_revision=NEW.revision AND o.base_revision=NEW.revision-1
 AND c.operation_id=NEW.operation_id AND p.effect_hash=e.effect_hash AND p.published_at=NEW.recorded_at)
BEGIN SELECT RAISE(ABORT,'Paper published prefix exact source required'); END;
CREATE INDEX paper_process_operations_base ON paper_process_operations(run_id,base_revision,operation_id);
