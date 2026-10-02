CREATE TABLE IF NOT EXISTS research_families (
 family_id TEXT PRIMARY KEY, namespace TEXT NOT NULL, symbol TEXT NOT NULL,
 selection_procedure TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_family_events (
 event_id TEXT PRIMARY KEY, family_id TEXT NOT NULL, kind TEXT NOT NULL,
 payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS research_family_event_order ON research_family_events(family_id,created_at,event_id);
CREATE TABLE IF NOT EXISTS research_finalists (
 finalist_id TEXT PRIMARY KEY, run_id TEXT NOT NULL UNIQUE, family_id TEXT NOT NULL,
 frozen_json TEXT NOT NULL, frozen_hash TEXT NOT NULL, frozen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_holdout_observations (
 observation_id TEXT PRIMARY KEY, finalist_id TEXT, family_id TEXT NOT NULL,
 namespace TEXT NOT NULL, symbol TEXT NOT NULL, start_at TEXT NOT NULL,
 end_at TEXT NOT NULL, kind TEXT NOT NULL, reference_hash TEXT NOT NULL, observed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS research_holdout_overlap ON research_holdout_observations(namespace,symbol,start_at,end_at);
CREATE TABLE IF NOT EXISTS research_holdout_results (
 finalist_id TEXT PRIMARY KEY, result_json TEXT NOT NULL, result_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS research_families_immutable BEFORE UPDATE ON research_families BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_families_no_delete BEFORE DELETE ON research_families BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_family_events_immutable BEFORE UPDATE ON research_family_events BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_family_events_no_delete BEFORE DELETE ON research_family_events BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_finalists_immutable BEFORE UPDATE ON research_finalists BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_finalists_no_delete BEFORE DELETE ON research_finalists BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_holdout_observations_immutable BEFORE UPDATE ON research_holdout_observations BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_holdout_observations_no_delete BEFORE DELETE ON research_holdout_observations BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_holdout_results_immutable BEFORE UPDATE ON research_holdout_results BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS research_holdout_results_no_delete BEFORE DELETE ON research_holdout_results BEGIN SELECT RAISE(ABORT,'research ledger is append-only'); END;
