-- r7-migration-transaction: atomic
CREATE INDEX paper_process_effects_revision ON paper_process_effects(run_id,checkpoint_revision,operation_id);
