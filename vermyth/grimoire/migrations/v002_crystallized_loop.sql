CREATE TABLE IF NOT EXISTS crystallized_sigils (
    name TEXT PRIMARY KEY,
    sigil_json TEXT NOT NULL,
    source_seed_id TEXT NOT NULL,
    crystallized_at TEXT NOT NULL,
    generation INTEGER NOT NULL DEFAULT 1,
    aspect_pattern_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crystallized_sigils_aspect
    ON crystallized_sigils (aspect_pattern_json);

ALTER TABLE glyph_seeds ADD COLUMN generation INTEGER NOT NULL DEFAULT 1;
ALTER TABLE cast_results ADD COLUMN provenance_json TEXT;
