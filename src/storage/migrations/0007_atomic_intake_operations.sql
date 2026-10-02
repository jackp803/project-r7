CREATE TABLE IF NOT EXISTS strategy_intake_operations (
    operation_id TEXT PRIMARY KEY,
    payload_hash TEXT NOT NULL,
    source_actor TEXT NOT NULL,
    intake_id TEXT NOT NULL UNIQUE REFERENCES strategy_intake_receipts(intake_id) ON DELETE RESTRICT
);
CREATE TRIGGER IF NOT EXISTS strategy_intake_operations_no_update
BEFORE UPDATE ON strategy_intake_operations
BEGIN SELECT RAISE(ABORT, 'intake operation is immutable'); END;
CREATE TRIGGER IF NOT EXISTS strategy_intake_operations_no_delete
BEFORE DELETE ON strategy_intake_operations
BEGIN SELECT RAISE(ABORT, 'intake operation is immutable'); END;
