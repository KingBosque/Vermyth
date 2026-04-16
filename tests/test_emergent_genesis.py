from datetime import datetime, timezone

from vermyth.schema import (
    CastResult,
    CastProvenance,
    EmergentAspect,
    FluidSigil,
    AspectID,
    Intent,
    IntentVector,
    ProjectionMethod,
    ResonanceScore,
    SemanticVector,
    SideEffectTolerance,
    ReversibilityClass,
    Verdict,
    VerdictType,
    EffectClass,
    ContradictionSeverity,
    Polarity,
)


def _fake_cast(idx: int) -> CastResult:
    vector = SemanticVector(components=(0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.95 + 0.01 * idx))
    intent = Intent(
        objective="observe drift",
        scope="lab",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    iv = IntentVector(
        vector=vector,
        projection_method=ProjectionMethod.PARTIAL,
        constraint_component=SemanticVector(components=(0, 0, 0, 0, 0, 0, 0)),
        semantic_component=None,
        confidence=0.6,
    )
    sigil = FluidSigil(
        name=f"F{idx}",
        aspects=frozenset({AspectID.MIND}),
        effect_class=EffectClass.EMERGENCE,
        resonance_ceiling=0.95,
        contradiction_severity=ContradictionSeverity.NONE,
        semantic_fingerprint=f"fp-{idx}",
        semantic_vector=vector,
        polarity=Polarity.POSITIVE,
        source_vector=vector,
        nearest_canonical="MIND+LIGHT",
        interpolation_weights={"MIND+LIGHT": 1.0},
    )
    verdict = Verdict(
        verdict_type=VerdictType.COHERENT,
        resonance=ResonanceScore(raw=0.9, adjusted=0.9, ceiling_applied=False, proof="ok"),
        effect_description="ok",
        incoherence_reason=None,
        casting_note="ok",
        intent_vector=iv,
    )
    return CastResult.model_construct(
        cast_id=f"cast-{idx}",
        intent=intent,
        sigil=sigil,
        verdict=verdict,
        timestamp=datetime.now(timezone.utc),
        immutable=True,
        lineage=None,
        glyph_seed_id=None,
        provenance=CastProvenance(source="fluid"),
    )


def test_propose_genesis_from_history(resonance_engine):
    history = [_fake_cast(i) for i in range(3)]
    proposals = resonance_engine.propose_genesis(
        history, min_cluster_size=2, min_unexplained_variance=0.1
    )
    assert proposals
    assert proposals[0].proposed_name.startswith("GENESIS_")


def test_accept_emergent_aspect_registers_aspect(tmp_grimoire):
    aspect = EmergentAspect(
        proposed_name="GENESIS_TEST",
        derived_polarity=1,
        derived_entropy=0.42,
        proposed_symbol="✧",
        centroid_vector=SemanticVector(components=(0, 0, 0, 0, 0, 0, 0.9)),
        support_count=20,
        mean_resonance=0.88,
        coherence_rate=0.9,
        evidence_cast_ids=["a", "b"],
    )
    tmp_grimoire.write_emergent_aspect(aspect)
    tmp_grimoire.review_emergent_aspect(aspect.genesis_id, reviewer="tester", note="looks good")
    accepted = tmp_grimoire.accept_emergent_aspect(aspect.genesis_id)
    assert accepted.status.value == "ACCEPTED"
