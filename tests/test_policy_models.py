from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from vermyth.engine.policy.rule_based import RuleBasedPolicyModel
from vermyth.engine.policy.threshold_tuned import ThresholdTunedPolicyModel
from vermyth.schema import DivergenceStatus, PolicyThresholds, VerdictType


def test_rule_based_and_threshold_tuned_parity_with_default_thresholds() -> None:
    rule = RuleBasedPolicyModel()
    tuned = ThresholdTunedPolicyModel()
    thresholds = PolicyThresholds()
    cases = [
        (VerdictType.COHERENT, 0.90, None, None),
        (VerdictType.COHERENT, 0.70, None, None),
        (VerdictType.PARTIAL, 0.60, None, None),
        (VerdictType.INCOHERENT, 0.20, None, None),
        (VerdictType.COHERENT, 0.80, DivergenceStatus.STABLE, None),
        (VerdictType.COHERENT, 0.80, DivergenceStatus.DRIFTING, 0.5),
    ]
    for verdict, adjusted, divergence, narrative in cases:
        assert rule.decide(
            verdict=verdict,
            adjusted_resonance=adjusted,
            divergence_status=divergence,
            narrative_coherence=narrative,
            thresholds=thresholds,
        )[0] == tuned.decide(
            verdict=verdict,
            adjusted_resonance=adjusted,
            divergence_status=divergence,
            narrative_coherence=narrative,
            thresholds=thresholds,
        )[0]


def test_threshold_tuned_can_change_actions() -> None:
    with TemporaryDirectory() as td:
        tuned_path = Path(td) / "tuned.json"
        tuned_path.write_text(
            json.dumps(
                {
                    "thresholds": {
                        "allow_min_resonance": 0.95,
                        "reshape_min_resonance": 0.30,
                        "max_drift_status": "DRIFTING",
                    }
                }
            ),
            encoding="utf-8",
        )
        tuned = ThresholdTunedPolicyModel(thresholds_path=tuned_path)
    rule = RuleBasedPolicyModel()
    thresholds = PolicyThresholds()
    verdict = VerdictType.COHERENT
    adjusted = 0.80
    rule_action, _ = rule.decide(
        verdict=verdict,
        adjusted_resonance=adjusted,
        divergence_status=DivergenceStatus.STABLE,
        narrative_coherence=None,
        thresholds=thresholds,
    )
    tuned_action, _ = tuned.decide(
        verdict=verdict,
        adjusted_resonance=adjusted,
        divergence_status=DivergenceStatus.STABLE,
        narrative_coherence=None,
        thresholds=thresholds,
    )
    assert rule_action != tuned_action
