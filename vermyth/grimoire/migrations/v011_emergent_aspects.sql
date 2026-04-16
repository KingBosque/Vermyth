CREATE TABLE IF NOT EXISTS emergent_aspects (
    genesis_id TEXT PRIMARY KEY,
    proposed_name TEXT NOT NULL UNIQUE,
    derived_polarity INTEGER NOT NULL,
    derived_entropy REAL NOT NULL,
    proposed_symbol TEXT NOT NULL,
    centroid_vector_json TEXT NOT NULL,
    support_count INTEGER NOT NULL,
    mean_resonance REAL NOT NULL,
    coherence_rate REAL NOT NULL,
    status TEXT NOT NULL,
    proposed_at TEXT NOT NULL,
    decided_at TEXT,
    evidence_cast_ids_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_emergent_aspects_status
    ON emergent_aspects(status);
