"""Tests for additive arcane presentation (presentation-only; no new semantics)."""

from vermyth.arcane.presentation.transcript import arcane_transcript_for_cast_result
from vermyth.schema._legacy import (
    AspectID,
    CastResult,
    ContradictionSeverity,
    EffectClass,
    Intent,
    Lineage,
    ReversibilityClass,
    SideEffectTolerance,
    Sigil,
)
from tests.test_schema import _minimal_verdict


def test_arcane_transcript_structure_and_presentation_only_flag():
    intent = Intent(
        objective="obj",
        scope="scp",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    sigil = Sigil(
        name="TestSigil",
        aspects=frozenset({AspectID.VOID, AspectID.FORM}),
        effect_class=EffectClass.NEGATION,
        resonance_ceiling=0.9,
        contradiction_severity=ContradictionSeverity.SOFT,
    )
    cr = CastResult(intent=intent, sigil=sigil, verdict=_minimal_verdict())
    tr = arcane_transcript_for_cast_result(cr)

    assert tr["kind"] == "arcane_transcript"
    assert tr["version"] == 1
    assert tr["presentation_only"] is True
    phases = tr["phases"]
    assert [p["phase"] for p in phases] == [
        "attunement",
        "warding",
        "casting",
        "verification",
        "residue",
    ]
    ward = next(p for p in phases if p["phase"] == "warding")
    assert ward["applicable"] is False
    att = next(p for p in phases if p["phase"] == "attunement")
    assert att["detail"]["objective"] == "obj"
    assert att["detail"]["scope"] == "scp"
    cas = next(p for p in phases if p["phase"] == "casting")
    assert cas["detail"]["sigil_name"] == "TestSigil"
    assert cas["detail"]["resonance_adjusted"] == 0.5
    res = next(p for p in phases if p["phase"] == "residue")
    assert res["detail"]["cast_id"] == cr.cast_id
    assert res["detail"]["lineage_parent_cast_id"] is None


def test_arcane_transcript_includes_lineage_when_present():
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.PARTIAL,
        side_effect_tolerance=SideEffectTolerance.NONE,
    )
    sigil = Sigil(
        name="n",
        aspects=frozenset({AspectID.MOTION}),
        effect_class=EffectClass.FORCE,
        resonance_ceiling=0.5,
        contradiction_severity=ContradictionSeverity.NONE,
    )
    lin = Lineage(parent_cast_id="parent-ulid", depth=1, branch_id="01ARZ3NDEKTSV4RRFFQ69G5FAV")
    cr = CastResult(
        intent=intent,
        sigil=sigil,
        verdict=_minimal_verdict(),
        lineage=lin,
    )
    tr = arcane_transcript_for_cast_result(cr)
    res = next(p for p in tr["phases"] if p["phase"] == "residue")
    assert res["detail"]["lineage_parent_cast_id"] == "parent-ulid"
    assert res["detail"]["lineage_depth"] == 1
