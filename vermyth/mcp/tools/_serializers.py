from __future__ import annotations

from typing import Any

from vermyth.schema import PolicyDecision


def policy_decision_to_dict(decision: PolicyDecision) -> dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "action": decision.action.value,
        "rationale": decision.rationale,
        "cast_id": decision.cast_id,
        "suggested_intent": (
            decision.suggested_intent.model_dump(mode="json")
            if decision.suggested_intent is not None
            else None
        ),
        "parent_cast_id": decision.parent_cast_id,
        "divergence_status": (
            decision.divergence_status.value
            if decision.divergence_status is not None
            else None
        ),
        "narrative_coherence": decision.narrative_coherence,
        "thresholds": decision.thresholds.model_dump(mode="json"),
        "model_name": decision.model_name,
        "model_version": decision.model_version,
        "timestamp": decision.timestamp.isoformat(),
    }

