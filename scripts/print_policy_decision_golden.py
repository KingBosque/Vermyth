#!/usr/bin/env python3
"""
Optional helper: print `policy_decision_to_dict` JSON for the same fixed PolicyDecision
inputs as `typescript/src/mcp/policy-decision-json.golden.test.ts`.

Not run in CI. Useful for spot-checking that Python's logical fields match the test inputs.

The committed TS golden uses ``Date.toISOString()`` (``...Z``) for ``timestamp``; Python's
``policy_decision_to_dict`` may emit an equivalent instant with a different string form
(``...+00:00``). Compare field-by-field or normalize ``timestamp`` before raw diff.

Usage (from repo root, with `pip install -e .`):

  python scripts/print_policy_decision_golden.py          # ALLOW branch
  python scripts/print_policy_decision_golden.py reshape  # RESHAPE + suggested_intent
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from vermyth.mcp.tools._serializers import policy_decision_to_dict
from vermyth.schema import PolicyAction, PolicyDecision, PolicyThresholds, ScoreComponent
from vermyth.schema._legacy import Intent, ReversibilityClass, SideEffectTolerance


def decision_allow() -> PolicyDecision:
    return PolicyDecision(
        decision_id="01JDECISIONABCDEFGHJKMNPQR",
        action=PolicyAction.ALLOW,
        rationale="Golden parity: coherent cast above allow threshold.",
        cast_id="01HZX8Q4K9ABCDEFGHJKMNPQRS",
        suggested_intent=None,
        parent_cast_id=None,
        divergence_status=None,
        narrative_coherence=None,
        thresholds=PolicyThresholds(),
        scores=[
            ScoreComponent(
                name="resonance",
                value=0.82,
                weight=0.5,
                explanation="adjusted resonance 0.820",
            ),
            ScoreComponent(
                name="divergence",
                value=1.0,
                weight=0.2,
                explanation="divergence stable",
            ),
            ScoreComponent(
                name="narrative",
                value=0.5,
                weight=0.1,
                explanation="narrative n/a",
            ),
            ScoreComponent(
                name="effect_risk",
                value=0.9,
                weight=0.2,
                explanation="effect risk ok",
            ),
        ],
        explanation=(
            "aggregate=0.500; resonance=0.820, divergence=1.000, narrative=0.500, effect_risk=0.900"
        ),
        model_name="rule_based",
        model_version="1",
        timestamp=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


def decision_reshape() -> PolicyDecision:
    return PolicyDecision(
        decision_id="01JRESHAPEABCDEFGHJKMNOPQ1",
        action=PolicyAction.RESHAPE,
        rationale="Golden parity: partial coherence; suggest intent refinement.",
        cast_id="01HZX8Q4K9ABCDEFGHJKMNPQR2",
        suggested_intent=Intent(
            objective="Refined objective for reshape",
            scope="golden reshape scope",
            reversibility=ReversibilityClass.PARTIAL,
            side_effect_tolerance=SideEffectTolerance.MEDIUM,
        ),
        parent_cast_id=None,
        divergence_status=None,
        narrative_coherence=0.55,
        thresholds=PolicyThresholds(),
        scores=[
            ScoreComponent(
                name="resonance",
                value=0.52,
                weight=0.5,
                explanation="adjusted resonance 0.520",
            ),
            ScoreComponent(
                name="divergence",
                value=0.85,
                weight=0.2,
                explanation="divergence drifting",
            ),
            ScoreComponent(
                name="narrative",
                value=0.4,
                weight=0.1,
                explanation="narrative weak",
            ),
            ScoreComponent(
                name="effect_risk",
                value=0.7,
                weight=0.2,
                explanation="effect risk moderate",
            ),
        ],
        explanation=(
            "aggregate=0.520; resonance=0.520, divergence=0.850, narrative=0.400, effect_risk=0.700"
        ),
        model_name="rule_based",
        model_version="1",
        timestamp=datetime(2024, 7, 20, 15, 30, 0, tzinfo=timezone.utc),
    )


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if mode in ("reshape", "resh"):
        decision = decision_reshape()
    else:
        decision = decision_allow()
    out = policy_decision_to_dict(decision)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
