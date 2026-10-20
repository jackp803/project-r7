-- r7-migration-transaction: atomic
CREATE UNIQUE INDEX product_entry_decisions_run_decision ON product_entry_decisions(run_id,decision_id);
CREATE TABLE product_exit_anchors (
 run_id TEXT NOT NULL, entry_decision_id TEXT NOT NULL,
 evidence_json TEXT NOT NULL, evidence_hash TEXT NOT NULL,
 generation INTEGER NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(run_id,entry_decision_id),
 UNIQUE(run_id,entry_decision_id,evidence_hash),
 FOREIGN KEY(run_id,entry_decision_id) REFERENCES product_entry_decisions(run_id,decision_id),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TABLE product_exit_decisions (
 run_id TEXT NOT NULL, entry_decision_id TEXT NOT NULL, decision_id TEXT NOT NULL UNIQUE,
 evidence_json TEXT NOT NULL, evidence_hash TEXT NOT NULL, effects_hash TEXT NOT NULL,
 anchor_evidence_hash TEXT NOT NULL, generation INTEGER NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(run_id,entry_decision_id),
 UNIQUE(run_id,entry_decision_id,decision_id,evidence_hash,effects_hash),
 FOREIGN KEY(run_id,entry_decision_id) REFERENCES product_entry_decisions(run_id,decision_id),
 FOREIGN KEY(run_id,entry_decision_id,anchor_evidence_hash)
  REFERENCES product_exit_anchors(run_id,entry_decision_id,evidence_hash),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TABLE product_exit_publications (
 run_id TEXT NOT NULL, entry_decision_id TEXT NOT NULL, decision_id TEXT NOT NULL UNIQUE,
 evidence_hash TEXT NOT NULL, effects_hash TEXT NOT NULL,
 generation INTEGER NOT NULL, published_at TEXT NOT NULL,
 PRIMARY KEY(run_id,entry_decision_id),
 FOREIGN KEY(run_id,entry_decision_id,decision_id,evidence_hash,effects_hash)
  REFERENCES product_exit_decisions(run_id,entry_decision_id,decision_id,evidence_hash,effects_hash),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TRIGGER product_exit_anchors_no_update BEFORE UPDATE ON product_exit_anchors
BEGIN SELECT RAISE(ABORT,'Original exit record is immutable'); END;
CREATE TRIGGER product_exit_anchors_no_delete BEFORE DELETE ON product_exit_anchors
BEGIN SELECT RAISE(ABORT,'Original exit record is immutable'); END;
CREATE TRIGGER product_exit_anchors_no_replace BEFORE INSERT ON product_exit_anchors
WHEN EXISTS(SELECT 1 FROM product_exit_anchors WHERE run_id=NEW.run_id AND entry_decision_id=NEW.entry_decision_id)
BEGIN SELECT RAISE(ABORT,'Original exit replacement is forbidden'); END;
CREATE TRIGGER product_exit_decisions_no_update BEFORE UPDATE ON product_exit_decisions
BEGIN SELECT RAISE(ABORT,'Original exit record is immutable'); END;
CREATE TRIGGER product_exit_decisions_no_delete BEFORE DELETE ON product_exit_decisions
BEGIN SELECT RAISE(ABORT,'Original exit record is immutable'); END;
CREATE TRIGGER product_exit_decisions_no_replace BEFORE INSERT ON product_exit_decisions
WHEN EXISTS(SELECT 1 FROM product_exit_decisions WHERE run_id=NEW.run_id AND entry_decision_id=NEW.entry_decision_id)
 OR EXISTS(SELECT 1 FROM product_exit_decisions WHERE decision_id=NEW.decision_id)
BEGIN SELECT RAISE(ABORT,'Original exit replacement is forbidden'); END;
CREATE TRIGGER product_exit_publications_no_update BEFORE UPDATE ON product_exit_publications
BEGIN SELECT RAISE(ABORT,'Original exit record is immutable'); END;
CREATE TRIGGER product_exit_publications_no_delete BEFORE DELETE ON product_exit_publications
BEGIN SELECT RAISE(ABORT,'Original exit record is immutable'); END;
CREATE TRIGGER product_exit_publications_no_replace BEFORE INSERT ON product_exit_publications
WHEN EXISTS(SELECT 1 FROM product_exit_publications WHERE run_id=NEW.run_id AND entry_decision_id=NEW.entry_decision_id)
 OR EXISTS(SELECT 1 FROM product_exit_publications WHERE decision_id=NEW.decision_id)
BEGIN SELECT RAISE(ABORT,'Original exit replacement is forbidden'); END;
