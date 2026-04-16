CREATE TABLE IF NOT EXISTS divergence_reports (
    cast_id TEXT PRIMARY KEY,
    parent_cast_id TEXT NOT NULL,
    l2_magnitude REAL NOT NULL,
    cosine_distance REAL NOT NULL,
    status TEXT NOT NULL,
    computed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS divergence_thresholds (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    l2_stable_max REAL NOT NULL,
    l2_diverged_min REAL NOT NULL,
    cosine_stable_max REAL NOT NULL,
    cosine_diverged_min REAL NOT NULL,
    updated_at TEXT NOT NULL
);
