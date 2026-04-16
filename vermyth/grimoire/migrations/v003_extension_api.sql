CREATE TABLE IF NOT EXISTS registered_aspects (
    name TEXT PRIMARY KEY,
    polarity INTEGER NOT NULL,
    entropy_coefficient REAL NOT NULL,
    symbol TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    registered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS registered_sigils (
    name TEXT PRIMARY KEY,
    aspects_json TEXT NOT NULL,
    effect_class TEXT NOT NULL,
    resonance_ceiling REAL NOT NULL,
    contradiction_severity TEXT NOT NULL,
    is_override INTEGER NOT NULL DEFAULT 0,
    registered_at TEXT NOT NULL
);

