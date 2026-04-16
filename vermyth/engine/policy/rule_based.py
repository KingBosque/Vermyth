from __future__ import annotations

from vermyth.engine.policy.base import PolicyModel
from vermyth.schema import DivergenceStatus, PolicyAction, PolicyThresholds, VerdictType


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
        thresholds: PolicyThresholds,
    ) -> tuple[PolicyAction, str]:
        drift_ok = divergence_status is None or divergence_status in (
            DivergenceStatus.STABLE,
            thresholds.max_drift_status,
        )
        if verdict == VerdictType.INCOHERENT or divergence_status == DivergenceStatus.DIVERGED:
            action = PolicyAction.DENY
        elif (
            verdict == VerdictType.COHERENT
            and adjusted_resonance >= float(thresholds.allow_min_resonance)
            and drift_ok
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
        rationale_parts.append(f"decision={action.value}")
        return action, "; ".join(rationale_parts)
