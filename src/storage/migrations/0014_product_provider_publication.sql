-- r7-migration-transaction: atomic
CREATE TABLE product_dispatch_outbox (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, observed_at TEXT NOT NULL,
 effects_json TEXT NOT NULL, effects_hash TEXT NOT NULL,
 PRIMARY KEY(run_id,operation_id,observed_at),
 FOREIGN KEY(run_id,operation_id,observed_at) REFERENCES product_dispatch_observations(run_id,operation_id,observed_at)
);
CREATE TABLE product_dispatch_publications (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, observed_at TEXT NOT NULL,
 effects_hash TEXT NOT NULL, generation INTEGER NOT NULL, published_at TEXT NOT NULL,
 PRIMARY KEY(run_id,operation_id,observed_at),
 FOREIGN KEY(run_id,operation_id,observed_at) REFERENCES product_dispatch_outbox(run_id,operation_id,observed_at),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TRIGGER product_dispatch_outbox_no_update BEFORE UPDATE ON product_dispatch_outbox
BEGIN SELECT RAISE(ABORT,'Dispatch canonical effects are immutable'); END;
CREATE TRIGGER product_dispatch_outbox_no_delete BEFORE DELETE ON product_dispatch_outbox
BEGIN SELECT RAISE(ABORT,'Dispatch canonical effects are immutable'); END;
CREATE TRIGGER product_dispatch_publications_no_update BEFORE UPDATE ON product_dispatch_publications
BEGIN SELECT RAISE(ABORT,'Dispatch publication receipt is immutable'); END;
CREATE TRIGGER product_dispatch_publications_no_delete BEFORE DELETE ON product_dispatch_publications
BEGIN SELECT RAISE(ABORT,'Dispatch publication receipt is immutable'); END;
