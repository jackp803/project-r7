PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS paper_position_lifecycle_execution_bindings (
    lifecycle_execution_binding_id TEXT PRIMARY KEY,
    lifecycle_projection_id TEXT NOT NULL UNIQUE,
    position_id TEXT NOT NULL,
    lifecycle_revision INTEGER NOT NULL CHECK (lifecycle_revision >= 0),
    execution_interpreted_at TEXT NOT NULL,
    execution_scope TEXT NOT NULL
        CHECK (execution_scope = 'POSITION_LINKED_REDUCTION_ORDERS_V0_1'),
    execution_snapshot_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    persisted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (lifecycle_projection_id)
        REFERENCES paper_position_lifecycle_projections(lifecycle_projection_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_paper_lifecycle_execution_binding_position_revision
ON paper_position_lifecycle_execution_bindings(position_id, lifecycle_revision);

CREATE TRIGGER IF NOT EXISTS paper_lifecycle_execution_binding_immutable_update
BEFORE UPDATE ON paper_position_lifecycle_execution_bindings
BEGIN
    SELECT RAISE(ABORT, 'lifecycle execution binding is immutable');
END;

CREATE TRIGGER IF NOT EXISTS paper_lifecycle_execution_binding_immutable_delete
BEFORE DELETE ON paper_position_lifecycle_execution_bindings
BEGIN
    SELECT RAISE(ABORT, 'lifecycle execution binding is immutable');
END;
