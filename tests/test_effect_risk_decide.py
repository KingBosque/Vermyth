"""Effect-risk plumbing and policy gate (effect_risk_min_score)."""

from __future__ import annotations

from vermyth.schema import EffectType, PolicyThresholds


def test_deny_when_effect_risk_below_threshold_despite_coherent_verdict(make_tools) -> None:
    """
    High-risk world-model effects can trigger DENY via ``effect_risk_min_score``,
    independent of resonance alone.
    """
    tools = make_tools
    intent = {
        "objective": "Reveal hidden structure",
        "scope": "analysis",
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "LOW",
    }
    risky_effects = [
        {"effect_type": "WRITE", "reversible": False},
        {"effect_type": "WRITE", "reversible": False},
    ]
    thresholds = PolicyThresholds(
        effect_risk_min_score=0.5,
        scorer_weights={
            "resonance": 0.5,
            "divergence": 0.2,
            "narrative": 0.1,
            "effect_risk": 0.2,
        },
    )
    out = tools.tool_decide(
        intent=intent,
        aspects=["MIND", "LIGHT"],
        effects=risky_effects,
        thresholds=thresholds.model_dump(mode="json"),
    )
    assert out["decision"]["action"] == "DENY"
    assert "effect_risk" in out["decision"]["rationale"].lower()
