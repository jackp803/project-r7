-- r7-migration-transaction: atomic
CREATE TABLE product_dispatch_stop_cleanup_claims (
 run_id TEXT NOT NULL, stop_operation_id TEXT NOT NULL, close_operation_id TEXT NOT NULL,
 native_algo_id TEXT NOT NULL, provider_ref TEXT NOT NULL, account_ref TEXT NOT NULL,
 identity_json TEXT NOT NULL, identity_hash TEXT NOT NULL,
 source_json TEXT NOT NULL, source_hash TEXT NOT NULL,
 claimed_at TEXT NOT NULL, generation INTEGER NOT NULL,
 PRIMARY KEY(run_id,stop_operation_id), UNIQUE(provider_ref,account_ref,native_algo_id),
 FOREIGN KEY(run_id,stop_operation_id) REFERENCES product_dispatch_claims(run_id,operation_id),
 FOREIGN KEY(run_id,close_operation_id) REFERENCES product_dispatch_claims(run_id,operation_id),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TRIGGER product_dispatch_stop_cleanup_claims_no_update BEFORE UPDATE ON product_dispatch_stop_cleanup_claims
BEGIN SELECT RAISE(ABORT,'Stop cleanup claim is immutable'); END;
CREATE TRIGGER product_dispatch_stop_cleanup_claims_no_delete BEFORE DELETE ON product_dispatch_stop_cleanup_claims
BEGIN SELECT RAISE(ABORT,'Stop cleanup claim is immutable'); END;
CREATE TRIGGER product_dispatch_stop_cleanup_claims_no_replace BEFORE INSERT ON product_dispatch_stop_cleanup_claims
WHEN EXISTS(SELECT 1 FROM product_dispatch_stop_cleanup_claims WHERE run_id=NEW.run_id AND stop_operation_id=NEW.stop_operation_id)
 OR EXISTS(SELECT 1 FROM product_dispatch_stop_cleanup_claims WHERE provider_ref=NEW.provider_ref AND account_ref=NEW.account_ref AND native_algo_id=NEW.native_algo_id)
BEGIN SELECT RAISE(ABORT,'Stop cleanup claim replacement is forbidden'); END;
