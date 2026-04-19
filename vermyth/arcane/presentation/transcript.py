"""Derive an inspectable arcane phase transcript from a :class:`CastResult`.

This module is **presentation-only**: it does not compute new scores, thresholds, or policy
outcomes. It maps existing fields to named phases so UIs or CLIs can show a disciplined
\"rite\" narrative without pretending extra semantics exist.

See ``docs/specs/technomancy-restoration.md``.
"""

from __future__ import annotations

from typing import Any

from vermyth.schema._legacy import CastResult


def arcane_transcript_for_cast_result(cast_result: CastResult) -> dict[str, Any]:
    """Return a deterministic, additive summary keyed by ritual phase labels.

    Warding is marked **not applicable** on a plain ``CastResult`` (no merged bundle
    thresholds on this object). Use policy/bundle artifacts for ward overlays.
    """
    iv = cast_result.verdict.intent_vector
    sigil = cast_result.sigil
    verdict = cast_result.verdict
    phases: list[dict[str, Any]] = [
        {
            "phase": "attunement",
            "mundane_anchor": "intent_and_projection",
            "detail": {
                "objective": cast_result.intent.objective,
                "scope": cast_result.intent.scope,
                "reversibility": cast_result.intent.reversibility.value,
                "side_effect_tolerance": cast_result.intent.side_effect_tolerance.value,
                "projection_method": iv.projection_method.value,
                "intent_confidence": iv.confidence,
            },
        },
        {
            "phase": "warding",
            "applicable": False,
            "mundane_anchor": "policy_threshold_merge",
            "note": (
                "No ward merge is attached to CastResult alone; "
                "bundles / decide merge wards into PolicyThresholds."
            ),
        },
        {
            "phase": "casting",
            "mundane_anchor": "composition_and_resonance",
            "detail": {
                "sigil_name": sigil.name,
                "effect_class": sigil.effect_class.value,
                "contradiction_severity": sigil.contradiction_severity.value,
                "resonance_adjusted": verdict.resonance.adjusted,
                "resonance_raw": verdict.resonance.raw,
                "ceiling_applied": verdict.resonance.ceiling_applied,
            },
        },
        {
            "phase": "verification",
            "mundane_anchor": "verdict_bands",
            "detail": {
                "verdict_type": verdict.verdict_type.value,
                "incoherence_reason": verdict.incoherence_reason,
            },
        },
        {
            "phase": "residue",
            "mundane_anchor": "identifiers_and_lineage",
            "detail": {
                "cast_id": cast_result.cast_id,
                "timestamp": cast_result.timestamp.isoformat(),
                "lineage_parent_cast_id": (
                    cast_result.lineage.parent_cast_id if cast_result.lineage else None
                ),
                "lineage_depth": cast_result.lineage.depth if cast_result.lineage else None,
                "branch_id": cast_result.lineage.branch_id if cast_result.lineage else None,
                "provenance_source": (
                    cast_result.provenance.source if cast_result.provenance else None
                ),
            },
        },
    ]

    return {
        "kind": "arcane_transcript",
        "version": 1,
        "presentation_only": True,
        "phases": phases,
    }
