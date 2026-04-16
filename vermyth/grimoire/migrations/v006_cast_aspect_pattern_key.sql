ALTER TABLE cast_results ADD COLUMN aspect_pattern_key TEXT;

CREATE INDEX IF NOT EXISTS idx_cast_results_aspect_pattern_key
    ON cast_results (aspect_pattern_key);

