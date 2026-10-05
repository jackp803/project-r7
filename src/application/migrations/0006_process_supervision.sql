CREATE TABLE IF NOT EXISTS process_generation_counters (
    role TEXT PRIMARY KEY CHECK (role IN ('control','research')),
    generation INTEGER NOT NULL CHECK (generation > 0)
);
CREATE TABLE IF NOT EXISTS process_sessions (
    role TEXT PRIMARY KEY CHECK (role IN ('control','research')),
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
CREATE TABLE IF NOT EXISTS process_session_history (
    role TEXT NOT NULL,
    generation INTEGER NOT NULL,
    process_generation_id TEXT NOT NULL UNIQUE,
    identity_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    state TEXT NOT NULL,
    PRIMARY KEY (role,generation)
);
