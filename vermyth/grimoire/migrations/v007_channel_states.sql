CREATE TABLE IF NOT EXISTS channel_states (
    branch_id TEXT PRIMARY KEY,
    cast_count INTEGER NOT NULL DEFAULT 0,
    cumulative_resonance REAL NOT NULL DEFAULT 0.0,
    mean_resonance REAL NOT NULL DEFAULT 0.0,
    coherence_streak INTEGER NOT NULL DEFAULT 0,
    last_verdict_type TEXT NOT NULL,
    status TEXT NOT NULL,
    last_cast_id TEXT NOT NULL,
    constraint_vector_json TEXT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_channel_states_status_updated_at
ON channel_states (status, updated_at DESC);

