CREATE TABLE IF NOT EXISTS policy_decisions (
    decision_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    cast_id TEXT NOT NULL,
    parent_cast_id TEXT,
    divergence_status TEXT,
    narrative_coherence REAL,
    thresholds_json TEXT NOT NULL,
    rationale TEXT NOT NULL,
    suggested_intent_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(cast_id) REFERENCES cast_results(cast_id)
);

CREATE INDEX IF NOT EXISTS idx_policy_decisions_action_created_at
    ON policy_decisions(action, created_at DESC);
