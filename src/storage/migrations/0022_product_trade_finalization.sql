-- r7-migration-transaction: atomic
CREATE TABLE product_dispatch_finalization_outbox (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, stop_operation_id TEXT NOT NULL,
 source_json TEXT NOT NULL, source_hash TEXT NOT NULL, effects_json TEXT NOT NULL, effects_hash TEXT NOT NULL,
 staged_at TEXT NOT NULL, generation INTEGER NOT NULL,
 PRIMARY KEY(run_id,operation_id),
 FOREIGN KEY(run_id,operation_id) REFERENCES product_dispatch_claims(run_id,operation_id),
 FOREIGN KEY(run_id,stop_operation_id) REFERENCES product_dispatch_stop_cleanup_claims(run_id,stop_operation_id),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TABLE product_dispatch_finalization_publications (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, source_hash TEXT NOT NULL, effects_hash TEXT NOT NULL,
 published_at TEXT NOT NULL, generation INTEGER NOT NULL,
 PRIMARY KEY(run_id,operation_id),
 FOREIGN KEY(run_id,operation_id) REFERENCES product_dispatch_finalization_outbox(run_id,operation_id),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TRIGGER product_dispatch_finalization_outbox_no_update BEFORE UPDATE ON product_dispatch_finalization_outbox
BEGIN SELECT RAISE(ABORT,'Finalization source and effects are immutable'); END;
CREATE TRIGGER product_dispatch_finalization_outbox_no_delete BEFORE DELETE ON product_dispatch_finalization_outbox
BEGIN SELECT RAISE(ABORT,'Finalization source and effects are immutable'); END;
CREATE TRIGGER product_dispatch_finalization_outbox_no_replace BEFORE INSERT ON product_dispatch_finalization_outbox
WHEN EXISTS(SELECT 1 FROM product_dispatch_finalization_outbox WHERE run_id=NEW.run_id AND operation_id=NEW.operation_id)
BEGIN SELECT RAISE(ABORT,'Finalization replacement is forbidden'); END;
CREATE TRIGGER product_dispatch_finalization_publications_no_update BEFORE UPDATE ON product_dispatch_finalization_publications
BEGIN SELECT RAISE(ABORT,'Finalization receipt is immutable'); END;
CREATE TRIGGER product_dispatch_finalization_publications_no_delete BEFORE DELETE ON product_dispatch_finalization_publications
BEGIN SELECT RAISE(ABORT,'Finalization receipt is immutable'); END;
CREATE TRIGGER product_dispatch_finalization_publications_no_replace BEFORE INSERT ON product_dispatch_finalization_publications
WHEN EXISTS(SELECT 1 FROM product_dispatch_finalization_publications WHERE run_id=NEW.run_id AND operation_id=NEW.operation_id)
BEGIN SELECT RAISE(ABORT,'Finalization receipt replacement is forbidden'); END;
