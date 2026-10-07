-- r7-migration-transaction: atomic
CREATE TABLE product_qualification_receipts (
 execution_id TEXT PRIMARY KEY CHECK(length(execution_id) BETWEEN 1 AND 128),
 receipt_id TEXT NOT NULL UNIQUE CHECK(length(receipt_id)=78),
 namespace TEXT NOT NULL CHECK(namespace IN ('FIXTURE','LOCAL_RESEARCH')),
 subject_hash TEXT NOT NULL CHECK(length(subject_hash)=71),
 inventory_hash TEXT NOT NULL CHECK(length(inventory_hash)=71),
 payload_json TEXT NOT NULL CHECK(length(payload_json) BETWEEN 1 AND 1048576),
 payload_hash TEXT NOT NULL CHECK(length(payload_hash)=71),
 started_at TEXT NOT NULL,
 finished_at TEXT NOT NULL
);
CREATE TRIGGER product_qualification_receipts_namespace BEFORE INSERT ON product_qualification_receipts
WHEN (SELECT namespace FROM registry_research_namespace WHERE singleton=1) IS NOT NEW.namespace
BEGIN SELECT RAISE(ABORT,'qualification receipt namespace differs from canonical owner'); END;
CREATE TRIGGER product_qualification_receipts_no_replace BEFORE INSERT ON product_qualification_receipts
WHEN EXISTS(SELECT 1 FROM product_qualification_receipts
 WHERE execution_id=NEW.execution_id OR receipt_id=NEW.receipt_id)
BEGIN SELECT RAISE(ABORT,'qualification receipts cannot be replaced'); END;
CREATE TRIGGER product_qualification_receipts_no_update BEFORE UPDATE ON product_qualification_receipts
BEGIN SELECT RAISE(ABORT,'qualification receipts are immutable'); END;
CREATE TRIGGER product_qualification_receipts_no_delete BEFORE DELETE ON product_qualification_receipts
BEGIN SELECT RAISE(ABORT,'qualification receipts cannot be deleted'); END;
