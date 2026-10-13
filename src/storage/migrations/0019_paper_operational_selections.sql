-- r7-migration-transaction: atomic
CREATE TABLE paper_operational_selections (
    generation INTEGER PRIMARY KEY CHECK(generation BETWEEN 1 AND 2147483647),
    config_hash TEXT NOT NULL,
    selection_json TEXT NOT NULL,
    selection_hash TEXT NOT NULL
);
CREATE TRIGGER paper_operational_selections_no_update BEFORE UPDATE ON paper_operational_selections
BEGIN SELECT RAISE(ABORT,'Paper selection is immutable'); END;
CREATE TRIGGER paper_operational_selections_no_delete BEFORE DELETE ON paper_operational_selections
BEGIN SELECT RAISE(ABORT,'Paper selection cannot be deleted'); END;
CREATE TRIGGER paper_operational_selections_no_replace BEFORE INSERT ON paper_operational_selections
WHEN EXISTS(SELECT 1 FROM paper_operational_selections WHERE generation=NEW.generation)
BEGIN SELECT RAISE(ABORT,'Paper selection cannot be replaced'); END;
CREATE TRIGGER paper_operational_selections_sequential BEFORE INSERT ON paper_operational_selections
WHEN NEW.generation != COALESCE((SELECT MAX(generation)+1 FROM paper_operational_selections),1)
BEGIN SELECT RAISE(ABORT,'Paper selection must be sequential'); END;
