CREATE TABLE IF NOT EXISTS control_namespace(
    singleton INTEGER PRIMARY KEY CHECK(singleton=1), namespace TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS control_commands(
    command_id TEXT PRIMARY KEY, operation TEXT NOT NULL, resource TEXT NOT NULL,
    actor TEXT NOT NULL, request_json TEXT NOT NULL, request_hash TEXT NOT NULL,
    expected_revision INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('PREPARED','COMPLETE')),
    generation INTEGER NOT NULL, nonce TEXT NOT NULL, lease_deadline TEXT NOT NULL,
    prepared_at TEXT NOT NULL, completed_at TEXT, receipt_json TEXT, receipt_hash TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS control_one_pending_resource
    ON control_commands(resource) WHERE status='PREPARED';
CREATE TRIGGER IF NOT EXISTS control_completed_immutable BEFORE UPDATE ON control_commands
    WHEN OLD.status='COMPLETE'
    BEGIN SELECT RAISE(ABORT,'Completed command is immutable'); END;
CREATE TRIGGER IF NOT EXISTS control_no_delete BEFORE DELETE ON control_commands
    BEGIN SELECT RAISE(ABORT,'Command audit is retained'); END;
