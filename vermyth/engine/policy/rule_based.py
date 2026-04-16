from __future__ import annotations

from vermyth.engine.policy.base import PolicyModel
from vermyth.schema import (
    DivergenceStatus,
    PolicyAction,
    PolicyThresholds,
    ScoreComponent,
    VerdictType,
)


class RuleBasedPolicyModel(PolicyModel):
    name = "rule_based"
    version = "1"

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
        drift_ok = divergence_status is None or divergence_status in (
            DivergenceStatus.STABLE,
            thresholds.max_drift_status,
        )
        effect_sc = next((c for c in scores if c.name == "effect_risk"), None)
        if (
            thresholds.effect_risk_min_score is not None
            and effect_sc is not None
            and effect_sc.weight > 0
            and float(effect_sc.value) < float(thresholds.effect_risk_min_score)
        ):
            return (
                PolicyAction.DENY,
                f"verdict={verdict.value}; effect_risk={effect_sc.value:.3f} below min "
                f"{thresholds.effect_risk_min_score:.3f}; {effect_sc.explanation}",
            )
        if verdict == VerdictType.INCOHERENT or divergence_status == DivergenceStatus.DIVERGED:
            action = PolicyAction.DENY
        elif (
            verdict == VerdictType.COHERENT
            and adjusted_resonance >= float(thresholds.allow_min_resonance)
            and drift_ok
            and aggregate_score >= float(thresholds.allow_min_resonance)
        ):
            action = PolicyAction.ALLOW
        else:
            action = PolicyAction.RESHAPE

        rationale_parts = [
            f"verdict={verdict.value}",
            f"resonance={adjusted_resonance:.3f}",
        ]
        if divergence_status is not None:
            rationale_parts.append(f"drift={divergence_status.value}")
        if narrative_coherence is not None:
            rationale_parts.append(f"narrative={narrative_coherence:.3f}")
        rationale_parts.append(f"aggregate={aggregate_score:.3f}")
        rationale_parts.extend(
            [f"{c.name}:{c.value:.3f}x{c.weight:.2f}" for c in scores]
        )
        rationale_parts.append(f"decision={action.value}")
        return action, "; ".join(rationale_parts)
