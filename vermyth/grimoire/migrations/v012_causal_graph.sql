CREATE TABLE IF NOT EXISTS causal_edges (
    edge_id TEXT PRIMARY KEY,
    source_cast_id TEXT NOT NULL,
    target_cast_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    weight REAL NOT NULL,
    created_at TEXT NOT NULL,
    evidence TEXT,
    FOREIGN KEY (source_cast_id) REFERENCES cast_results(cast_id) ON DELETE CASCADE,
    FOREIGN KEY (target_cast_id) REFERENCES cast_results(cast_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_causal_edges_source
    ON causal_edges(source_cast_id);

CREATE INDEX IF NOT EXISTS idx_causal_edges_target
    ON causal_edges(target_cast_id);

CREATE INDEX IF NOT EXISTS idx_causal_edges_type_weight
    ON causal_edges(edge_type, weight);
