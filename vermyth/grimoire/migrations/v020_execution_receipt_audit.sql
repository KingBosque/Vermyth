ALTER TABLE execution_receipts ADD COLUMN signature TEXT;
ALTER TABLE execution_receipts ADD COLUMN signing_key_id TEXT;
ALTER TABLE execution_receipts ADD COLUMN correlation_id TEXT;
ALTER TABLE execution_receipts ADD COLUMN principal_id TEXT;
