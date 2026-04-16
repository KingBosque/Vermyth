CREATE INDEX IF NOT EXISTS idx_divergence_reports_status_computed_at
    ON divergence_reports (status, computed_at);

CREATE INDEX IF NOT EXISTS idx_cast_results_branch_id_timestamp
    ON cast_results (branch_id, timestamp);
