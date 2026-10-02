-- r7-migration-transaction: atomic
CREATE TABLE paper_process_runs (
 run_id TEXT PRIMARY KEY, binding_json TEXT NOT NULL, binding_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE paper_process_operations (
 run_id TEXT NOT NULL REFERENCES paper_process_runs(run_id), operation_id TEXT NOT NULL,
 base_revision INTEGER NOT NULL CHECK(base_revision>=0), request_json TEXT NOT NULL,
 request_hash TEXT NOT NULL, prepared_at TEXT NOT NULL,
 PRIMARY KEY(run_id,operation_id),
 FOREIGN KEY(run_id,base_revision) REFERENCES paper_process_checkpoints(run_id,revision)
);
CREATE TABLE paper_process_effects (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, checkpoint_revision INTEGER NOT NULL,
 outcome_json TEXT NOT NULL, outcome_hash TEXT NOT NULL, effect_hash TEXT NOT NULL,
 completed_at TEXT NOT NULL, PRIMARY KEY(run_id,operation_id),
 FOREIGN KEY(run_id,operation_id) REFERENCES paper_process_operations(run_id,operation_id),
 FOREIGN KEY(run_id,checkpoint_revision) REFERENCES paper_process_checkpoints(run_id,revision)
 DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE paper_process_checkpoints (
 run_id TEXT NOT NULL REFERENCES paper_process_runs(run_id), revision INTEGER NOT NULL CHECK(revision>=0),
 operation_id TEXT, state_json TEXT NOT NULL, state_hash TEXT NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(run_id,revision), UNIQUE(run_id,operation_id),
 FOREIGN KEY(run_id,operation_id) REFERENCES paper_process_effects(run_id,operation_id)
 DEFERRABLE INITIALLY DEFERRED,
 CHECK((revision=0 AND operation_id IS NULL) OR (revision>0 AND operation_id IS NOT NULL))
);
CREATE TABLE paper_process_publications (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, effect_hash TEXT NOT NULL, published_at TEXT NOT NULL,
 PRIMARY KEY(run_id,operation_id),
 FOREIGN KEY(run_id,operation_id) REFERENCES paper_process_effects(run_id,operation_id)
);
CREATE TABLE paper_process_generations (
 run_id TEXT NOT NULL REFERENCES paper_process_runs(run_id), generation INTEGER NOT NULL CHECK(generation>0),
 instance_id TEXT NOT NULL, started_at TEXT NOT NULL, PRIMARY KEY(run_id,generation), UNIQUE(run_id,instance_id)
);
CREATE TRIGGER paper_process_runs_no_update BEFORE UPDATE ON paper_process_runs
BEGIN SELECT RAISE(ABORT,'Paper run identity is immutable'); END;
CREATE TRIGGER paper_process_runs_no_delete BEFORE DELETE ON paper_process_runs
BEGIN SELECT RAISE(ABORT,'Paper run identity is immutable'); END;
CREATE TRIGGER paper_process_operations_no_update BEFORE UPDATE ON paper_process_operations
BEGIN SELECT RAISE(ABORT,'Paper operation intent is immutable'); END;
CREATE TRIGGER paper_process_operations_no_delete BEFORE DELETE ON paper_process_operations
BEGIN SELECT RAISE(ABORT,'Paper operation intent is immutable'); END;
CREATE TRIGGER paper_process_effects_no_update BEFORE UPDATE ON paper_process_effects
BEGIN SELECT RAISE(ABORT,'Paper operation effect is immutable'); END;
CREATE TRIGGER paper_process_effects_no_delete BEFORE DELETE ON paper_process_effects
BEGIN SELECT RAISE(ABORT,'Paper operation effect is immutable'); END;
CREATE TRIGGER paper_process_checkpoints_no_update BEFORE UPDATE ON paper_process_checkpoints
BEGIN SELECT RAISE(ABORT,'Paper checkpoint is immutable'); END;
CREATE TRIGGER paper_process_checkpoints_no_delete BEFORE DELETE ON paper_process_checkpoints
BEGIN SELECT RAISE(ABORT,'Paper checkpoint is immutable'); END;
CREATE TRIGGER paper_process_publications_no_update BEFORE UPDATE ON paper_process_publications
BEGIN SELECT RAISE(ABORT,'Paper publication receipt is immutable'); END;
CREATE TRIGGER paper_process_publications_no_delete BEFORE DELETE ON paper_process_publications
BEGIN SELECT RAISE(ABORT,'Paper publication receipt is immutable'); END;
CREATE TRIGGER paper_process_generations_no_update BEFORE UPDATE ON paper_process_generations
BEGIN SELECT RAISE(ABORT,'Paper process generation is immutable'); END;
CREATE TRIGGER paper_process_generations_no_delete BEFORE DELETE ON paper_process_generations
BEGIN SELECT RAISE(ABORT,'Paper process generation is immutable'); END;
