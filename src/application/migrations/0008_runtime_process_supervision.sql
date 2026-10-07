CREATE TABLE process_generation_counters_v0_2 (
    role TEXT PRIMARY KEY CHECK (role IN ('control','research','runtime','cloud')),
    generation INTEGER NOT NULL CHECK (generation > 0)
);
INSERT INTO process_generation_counters_v0_2 (role,generation)
    SELECT role,generation FROM process_generation_counters;
DROP TABLE process_generation_counters;
ALTER TABLE process_generation_counters_v0_2 RENAME TO process_generation_counters;

CREATE TABLE process_sessions_v0_2 (
    role TEXT PRIMARY KEY CHECK (role IN ('control','research','runtime','cloud')),
    generation INTEGER NOT NULL,
    process_generation_id TEXT NOT NULL UNIQUE,
    product_instance_id TEXT NOT NULL,
    pid INTEGER NOT NULL,
    config_hash TEXT NOT NULL,
    identity_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    heartbeat_sequence INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN
        ('RUNNING','STOPPED','FAILED','CONFIG_CHANGED','CLOCK_REGRESSION','SUPERVISION_STORAGE_FAILURE'))
);
INSERT INTO process_sessions_v0_2 (role,generation,process_generation_id,product_instance_id,pid,
    config_hash,identity_json,started_at,heartbeat_at,heartbeat_sequence,state)
    SELECT role,generation,process_generation_id,product_instance_id,pid,
        config_hash,identity_json,started_at,heartbeat_at,heartbeat_sequence,state FROM process_sessions;
DROP TABLE process_sessions;
ALTER TABLE process_sessions_v0_2 RENAME TO process_sessions;
