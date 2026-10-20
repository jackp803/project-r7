-- r7-migration-transaction: atomic
CREATE TABLE product_entry_decisions (
 run_id TEXT NOT NULL, boundary TEXT NOT NULL, decision_id TEXT NOT NULL UNIQUE,
 evidence_json TEXT NOT NULL, evidence_hash TEXT NOT NULL,
 effects_json TEXT NOT NULL, effects_hash TEXT NOT NULL,
 generation INTEGER NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(run_id,boundary),
 FOREIGN KEY(run_id) REFERENCES product_dispatch_runs(run_id),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TABLE product_entry_publications (
 run_id TEXT NOT NULL, boundary TEXT NOT NULL, decision_id TEXT NOT NULL,
 effects_hash TEXT NOT NULL, generation INTEGER NOT NULL, published_at TEXT NOT NULL,
 evidence_hash TEXT NOT NULL,
 PRIMARY KEY(run_id,boundary),
 FOREIGN KEY(run_id,boundary) REFERENCES product_entry_decisions(run_id,boundary),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TRIGGER product_entry_decisions_no_update BEFORE UPDATE ON product_entry_decisions
BEGIN SELECT RAISE(ABORT,'Entry decision is immutable'); END;
CREATE TRIGGER product_entry_decisions_no_delete BEFORE DELETE ON product_entry_decisions
BEGIN SELECT RAISE(ABORT,'Entry decision is immutable'); END;
CREATE TRIGGER product_entry_decisions_no_replace BEFORE INSERT ON product_entry_decisions
WHEN EXISTS(SELECT 1 FROM product_entry_decisions WHERE run_id=NEW.run_id AND boundary=NEW.boundary)
 OR EXISTS(SELECT 1 FROM product_entry_decisions WHERE decision_id=NEW.decision_id)
BEGIN SELECT RAISE(ABORT,'Entry decision replacement is forbidden'); END;
CREATE TRIGGER product_entry_publications_no_update BEFORE UPDATE ON product_entry_publications
BEGIN SELECT RAISE(ABORT,'Entry publication is immutable'); END;
CREATE TRIGGER product_entry_publications_no_delete BEFORE DELETE ON product_entry_publications
BEGIN SELECT RAISE(ABORT,'Entry publication is immutable'); END;
CREATE TRIGGER product_entry_publications_no_replace BEFORE INSERT ON product_entry_publications
WHEN EXISTS(SELECT 1 FROM product_entry_publications WHERE run_id=NEW.run_id AND boundary=NEW.boundary)
BEGIN SELECT RAISE(ABORT,'Entry publication replacement is forbidden'); END;
