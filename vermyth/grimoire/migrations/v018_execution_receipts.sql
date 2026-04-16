CREATE TABLE IF NOT EXISTS execution_receipts (
    receipt_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    status TEXT NOT NULL,
    nodes_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_execution_receipts_execution_id
    ON execution_receipts(execution_id);

