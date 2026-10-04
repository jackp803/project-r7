-- r7-migration-transaction: atomic
CREATE INDEX product_dispatch_account_claim_inventory
ON product_dispatch_intents(provider_ref,account_ref,json_extract(request_json,'$.role'),prepared_at,run_id,operation_id);
