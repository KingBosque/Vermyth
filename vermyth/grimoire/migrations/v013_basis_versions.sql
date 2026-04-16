CREATE TABLE IF NOT EXISTS basis_versions (
    version INTEGER PRIMARY KEY,
    dimensionality INTEGER NOT NULL,
    aspect_order_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO basis_versions (
    version, dimensionality, aspect_order_json, created_at
) VALUES (
    0,
    6,
    '["VOID","FORM","MOTION","MIND","DECAY","LIGHT"]',
    CURRENT_TIMESTAMP
);

ALTER TABLE cast_results ADD COLUMN basis_version INTEGER;
ALTER TABLE glyph_seeds ADD COLUMN basis_version INTEGER;
ALTER TABLE crystallized_sigils ADD COLUMN basis_version INTEGER;
ALTER TABLE channel_states ADD COLUMN basis_version INTEGER;
ALTER TABLE emergent_aspects ADD COLUMN basis_version INTEGER;

UPDATE cast_results SET basis_version = 0 WHERE basis_version IS NULL;
UPDATE glyph_seeds SET basis_version = 0 WHERE basis_version IS NULL;
UPDATE crystallized_sigils SET basis_version = 0 WHERE basis_version IS NULL;
UPDATE channel_states SET basis_version = 0 WHERE basis_version IS NULL;
UPDATE emergent_aspects SET basis_version = 0 WHERE basis_version IS NULL;
