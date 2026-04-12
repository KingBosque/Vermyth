CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cast_results (
    cast_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    intent_json TEXT NOT NULL,
    sigil_json TEXT NOT NULL,
    verdict_json TEXT NOT NULL,
    lineage_json TEXT,
    glyph_seed_id TEXT,
    semantic_vector_json TEXT NOT NULL,
    verdict_type TEXT NOT NULL,
    effect_class TEXT NOT NULL,
    adjusted_resonance REAL NOT NULL,
    branch_id TEXT
);

CREATE TABLE IF NOT EXISTS glyph_seeds (
    seed_id TEXT PRIMARY KEY,
    aspect_pattern_json TEXT NOT NULL,
    observed_count INTEGER NOT NULL DEFAULT 0,
    mean_resonance REAL NOT NULL DEFAULT 0.0,
    coherence_rate REAL NOT NULL DEFAULT 0.0,
    candidate_effect_class TEXT,
    crystallized INTEGER NOT NULL DEFAULT 0,
    semantic_vector_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cast_results_verdict_type
    ON cast_results (verdict_type);

CREATE INDEX IF NOT EXISTS idx_cast_results_effect_class
    ON cast_results (effect_class);

CREATE INDEX IF NOT EXISTS idx_cast_results_adjusted_resonance
    ON cast_results (adjusted_resonance);

CREATE INDEX IF NOT EXISTS idx_cast_results_branch_id
    ON cast_results (branch_id);

CREATE INDEX IF NOT EXISTS idx_glyph_seeds_crystallized
    ON glyph_seeds (crystallized);
