CREATE TABLE IF NOT EXISTS programs (
    program_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    nodes_json TEXT NOT NULL,
    entry_node_ids_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS program_executions (
    execution_id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    status TEXT NOT NULL,
    node_results_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    branch_id TEXT NOT NULL,
    FOREIGN KEY (program_id) REFERENCES programs(program_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_program_executions_program_id
    ON program_executions(program_id);
