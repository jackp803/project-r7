-- r7-migration-transaction: atomic
CREATE TABLE product_dispatch_funding_outbox (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, observed_at TEXT NOT NULL,
 funding_evidence_id TEXT NOT NULL, observation_json TEXT NOT NULL, observation_hash TEXT NOT NULL,
 effects_json TEXT NOT NULL, effects_hash TEXT NOT NULL, generation INTEGER NOT NULL,
 PRIMARY KEY(run_id,operation_id,observed_at),
 FOREIGN KEY(run_id,operation_id) REFERENCES product_dispatch_claims(run_id,operation_id),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TABLE product_dispatch_funding_publications (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, observed_at TEXT NOT NULL,
 effects_hash TEXT NOT NULL, generation INTEGER NOT NULL, published_at TEXT NOT NULL,
 PRIMARY KEY(run_id,operation_id,observed_at),
 FOREIGN KEY(run_id,operation_id,observed_at) REFERENCES product_dispatch_funding_outbox(run_id,operation_id,observed_at),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TRIGGER product_dispatch_funding_outbox_no_update BEFORE UPDATE ON product_dispatch_funding_outbox
BEGIN SELECT RAISE(ABORT,'Funding observation and effects are immutable'); END;
CREATE TRIGGER product_dispatch_funding_outbox_no_delete BEFORE DELETE ON product_dispatch_funding_outbox
BEGIN SELECT RAISE(ABORT,'Funding observation and effects are immutable'); END;
CREATE TRIGGER product_dispatch_funding_publications_no_update BEFORE UPDATE ON product_dispatch_funding_publications
BEGIN SELECT RAISE(ABORT,'Funding publication receipt is immutable'); END;
CREATE TRIGGER product_dispatch_funding_outbox_no_replace BEFORE INSERT ON product_dispatch_funding_outbox
WHEN EXISTS(SELECT 1 FROM product_dispatch_funding_outbox
 WHERE run_id=NEW.run_id AND operation_id=NEW.operation_id AND observed_at=NEW.observed_at)
BEGIN SELECT RAISE(ABORT,'Funding observation replacement is forbidden'); END;
CREATE TRIGGER product_dispatch_funding_publications_no_replace BEFORE INSERT ON product_dispatch_funding_publications
WHEN EXISTS(SELECT 1 FROM product_dispatch_funding_publications
 WHERE run_id=NEW.run_id AND operation_id=NEW.operation_id AND observed_at=NEW.observed_at)
BEGIN SELECT RAISE(ABORT,'Funding receipt replacement is forbidden'); END;
CREATE TRIGGER product_dispatch_funding_publications_no_delete BEFORE DELETE ON product_dispatch_funding_publications
BEGIN SELECT RAISE(ABORT,'Funding publication receipt is immutable'); END;
