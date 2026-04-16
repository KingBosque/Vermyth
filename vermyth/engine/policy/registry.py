from __future__ import annotations

from vermyth.engine.policy.rule_based import RuleBasedPolicyModel
from vermyth.engine.policy.threshold_tuned import ThresholdTunedPolicyModel

MODELS = {
    "rule_based": RuleBasedPolicyModel,
    "threshold_tuned": ThresholdTunedPolicyModel,
}
