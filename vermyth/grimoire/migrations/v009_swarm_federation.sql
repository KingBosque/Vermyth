CREATE TABLE IF NOT EXISTS swarms (
    swarm_id TEXT PRIMARY KEY,
    consensus_threshold REAL NOT NULL,
    status TEXT NOT NULL,
    aggregated_vector_json TEXT NOT NULL,
    last_cast_id TEXT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS swarm_members (
    swarm_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    vector_json TEXT NOT NULL,
    coherence_streak INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (swarm_id, session_id),
    FOREIGN KEY (swarm_id) REFERENCES swarms (swarm_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_swarm_members_session
ON swarm_members (session_id);
