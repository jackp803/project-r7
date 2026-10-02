-- r7-migration-transaction: atomic
CREATE TABLE product_dispatch_namespace (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), namespace TEXT NOT NULL CHECK(namespace IN ('FIXTURE','LOCAL_RESEARCH'))
);
CREATE TABLE product_dispatch_runs (
 run_id TEXT PRIMARY KEY, binding_json TEXT NOT NULL, binding_hash TEXT NOT NULL,
 provider_ref TEXT NOT NULL, account_ref TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE product_dispatch_generations (
 run_id TEXT NOT NULL REFERENCES product_dispatch_runs(run_id), generation INTEGER NOT NULL CHECK(generation>0),
 instance_id TEXT NOT NULL, started_at TEXT NOT NULL, PRIMARY KEY(run_id,generation), UNIQUE(run_id,instance_id)
);
CREATE TABLE product_dispatch_intents (
 run_id TEXT NOT NULL REFERENCES product_dispatch_runs(run_id), operation_id TEXT NOT NULL,
 request_json TEXT NOT NULL, request_hash TEXT NOT NULL, provider_ref TEXT NOT NULL,
 account_ref TEXT NOT NULL, native_client_id TEXT NOT NULL, prepared_at TEXT NOT NULL,
 PRIMARY KEY(run_id,operation_id), UNIQUE(provider_ref,account_ref,native_client_id)
);
CREATE TABLE product_dispatch_claims (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, generation INTEGER NOT NULL, dispatched_at TEXT NOT NULL,
 PRIMARY KEY(run_id,operation_id),
 FOREIGN KEY(run_id,operation_id) REFERENCES product_dispatch_intents(run_id,operation_id),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TABLE product_dispatch_observations (
 run_id TEXT NOT NULL, operation_id TEXT NOT NULL, observed_at TEXT NOT NULL,
 observation_json TEXT NOT NULL, observation_hash TEXT NOT NULL, generation INTEGER NOT NULL,
 PRIMARY KEY(run_id,operation_id,observed_at),
 FOREIGN KEY(run_id,operation_id) REFERENCES product_dispatch_claims(run_id,operation_id),
 FOREIGN KEY(run_id,generation) REFERENCES product_dispatch_generations(run_id,generation)
);
CREATE TRIGGER product_dispatch_namespace_no_update BEFORE UPDATE ON product_dispatch_namespace
BEGIN SELECT RAISE(ABORT,'Dispatch namespace is immutable'); END;
CREATE TRIGGER product_dispatch_namespace_no_delete BEFORE DELETE ON product_dispatch_namespace
BEGIN SELECT RAISE(ABORT,'Dispatch namespace is immutable'); END;
CREATE TRIGGER product_dispatch_runs_no_update BEFORE UPDATE ON product_dispatch_runs
BEGIN SELECT RAISE(ABORT,'Dispatch run identity is immutable'); END;
CREATE TRIGGER product_dispatch_runs_no_delete BEFORE DELETE ON product_dispatch_runs
BEGIN SELECT RAISE(ABORT,'Dispatch run identity is immutable'); END;
CREATE TRIGGER product_dispatch_generations_no_update BEFORE UPDATE ON product_dispatch_generations
BEGIN SELECT RAISE(ABORT,'Dispatch process history is immutable'); END;
CREATE TRIGGER product_dispatch_generations_no_delete BEFORE DELETE ON product_dispatch_generations
BEGIN SELECT RAISE(ABORT,'Dispatch process history is immutable'); END;
CREATE TRIGGER product_dispatch_intents_no_update BEFORE UPDATE ON product_dispatch_intents
BEGIN SELECT RAISE(ABORT,'Dispatch intent is immutable'); END;
CREATE TRIGGER product_dispatch_intents_no_delete BEFORE DELETE ON product_dispatch_intents
BEGIN SELECT RAISE(ABORT,'Dispatch intent is immutable'); END;
CREATE TRIGGER product_dispatch_claims_no_update BEFORE UPDATE ON product_dispatch_claims
BEGIN SELECT RAISE(ABORT,'Dispatch cannot be repeated'); END;
CREATE TRIGGER product_dispatch_claims_no_delete BEFORE DELETE ON product_dispatch_claims
BEGIN SELECT RAISE(ABORT,'Dispatch cannot be repeated'); END;
CREATE TRIGGER product_dispatch_observations_no_update BEFORE UPDATE ON product_dispatch_observations
BEGIN SELECT RAISE(ABORT,'Dispatch observations are immutable'); END;
CREATE TRIGGER product_dispatch_observations_no_delete BEFORE DELETE ON product_dispatch_observations
BEGIN SELECT RAISE(ABORT,'Dispatch observations are immutable'); END;
