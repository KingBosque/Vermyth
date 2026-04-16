from __future__ import annotations

import json
from pathlib import Path

from vermyth.engine.policy.base import PolicyModel
from vermyth.engine.policy.rule_based import RuleBasedPolicyModel
from vermyth.schema import (
    DivergenceStatus,
    PolicyAction,
    PolicyThresholds,
    ScoreComponent,
    VerdictType,
)


class ThresholdTunedPolicyModel(PolicyModel):
    name = "threshold_tuned"

    def __init__(self, *, thresholds_path: str | Path | None = None) -> None:
        self.version = "1"
        self._delegate = RuleBasedPolicyModel()
        self._thresholds_override: PolicyThresholds | None = None
        if thresholds_path is not None:
            payload = json.loads(Path(thresholds_path).read_text(encoding="utf-8"))
            thresholds = payload.get("thresholds", payload)
            self._thresholds_override = PolicyThresholds.model_validate(thresholds)

    def decide(
        self,
        *,
        verdict: VerdictType,
        adjusted_resonance: float,
        divergence_status: DivergenceStatus | None,
        narrative_coherence: float | None,
        scores: list[ScoreComponent],
        aggregate_score: float,
        thresholds: PolicyThresholds,
    ) -> tuple[PolicyAction, str]:
        active_thresholds = self._thresholds_override or thresholds
        return self._delegate.decide(
            verdict=verdict,
            adjusted_resonance=adjusted_resonance,
            divergence_status=divergence_status,
            narrative_coherence=narrative_coherence,
            scores=scores,
            aggregate_score=aggregate_score,
            thresholds=active_thresholds,
        )
