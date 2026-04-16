ALTER TABLE policy_decisions
    ADD COLUMN policy_model_name TEXT NOT NULL DEFAULT 'rule_based';

ALTER TABLE policy_decisions
    ADD COLUMN policy_model_version TEXT;
