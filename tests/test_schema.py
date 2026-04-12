import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest
from pydantic import ValidationError

from vermyth.schema import (
    ASPECT_CANONICAL_ORDER,
    AspectID,
    CastResult,
    ContradictionSeverity,
    EffectClass,
    GlyphSeed,
    Intent,
    IntentVector,
    Lineage,
    Polarity,
    ProjectionMethod,
    ResonanceScore,
    ReversibilityClass,
    SemanticQuery,
    SemanticVector,
    SideEffectTolerance,
    Sigil,
    Verdict,
    VerdictType,
)


@pytest.mark.parametrize(
    "member,polarity,entropy,symbol",
    [
        (AspectID.VOID, -1, 0.95, "◯"),
        (AspectID.FORM, 1, 0.15, "⬡"),
        (AspectID.MOTION, 1, 0.55, "⟳"),
        (AspectID.MIND, 1, 0.35, "◈"),
        (AspectID.DECAY, -1, 0.85, "※"),
        (AspectID.LIGHT, 1, 0.05, "✦"),
    ],
)
def test_aspect_id_properties(member, polarity, entropy, symbol):
    assert member.polarity == polarity
    assert member.entropy_coefficient == entropy
    assert member.symbol == symbol


def test_aspect_id_canonical_ordering_stable():
    assert ASPECT_CANONICAL_ORDER == (
        AspectID.VOID,
        AspectID.FORM,
        AspectID.MOTION,
        AspectID.MIND,
        AspectID.DECAY,
        AspectID.LIGHT,
    )
    assert [a.name for a in ASPECT_CANONICAL_ORDER] == [
        "VOID",
        "FORM",
        "MOTION",
        "MIND",
        "DECAY",
        "LIGHT",
    ]


def test_semantic_vector_components_from_known_aspects():
    aspects = frozenset({AspectID.FORM, AspectID.LIGHT})
    v = SemanticVector.from_aspects(aspects)
    expected = [0.0, 0.15 * 1.0, 0.0, 0.0, 0.0, 0.05 * 1.0]
    assert list(v.components) == expected


def test_semantic_vector_cosine_identical_is_one():
    v = SemanticVector.from_aspects(frozenset({AspectID.MIND}))
    assert v.cosine_similarity(v) == pytest.approx(1.0)


def test_semantic_vector_cosine_zero_vector_returns_zero():
    zero = SemanticVector(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    other = SemanticVector.from_aspects(frozenset({AspectID.FORM}))
    assert zero.cosine_similarity(other) == 0.0
    assert other.cosine_similarity(zero) == 0.0


def test_semantic_vector_distance_is_one_minus_cosine():
    a = SemanticVector.from_aspects(frozenset({AspectID.VOID}))
    b = SemanticVector.from_aspects(frozenset({AspectID.DECAY}))
    cos = a.cosine_similarity(b)
    assert a.distance(b) == pytest.approx(1.0 - cos)


def _fingerprint_for_aspects(aspects: frozenset[AspectID]) -> str:
    joined = "+".join(sorted(x.name for x in aspects))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def test_sigil_semantic_fingerprint_deterministic():
    a = frozenset({AspectID.MIND, AspectID.VOID})
    s1 = Sigil(
        name="s1",
        aspects=a,
        effect_class=EffectClass.MANIFESTATION,
        resonance_ceiling=0.5,
        contradiction_severity=ContradictionSeverity.NONE,
    )
    s2 = Sigil(
        name="s2",
        aspects=frozenset({AspectID.VOID, AspectID.MIND}),
        effect_class=EffectClass.MANIFESTATION,
        resonance_ceiling=0.5,
        contradiction_severity=ContradictionSeverity.NONE,
    )
    assert s1.semantic_fingerprint == s2.semantic_fingerprint
    assert s1.semantic_fingerprint == _fingerprint_for_aspects(a)


def test_sigil_semantic_vector_matches_manual():
    aspects = frozenset({AspectID.MOTION, AspectID.DECAY})
    s = Sigil(
        name="n",
        aspects=aspects,
        effect_class=EffectClass.COGNITION,
        resonance_ceiling=0.2,
        contradiction_severity=ContradictionSeverity.SOFT,
    )
    assert s.semantic_vector.components == SemanticVector.from_aspects(aspects).components


@pytest.mark.parametrize(
    "aspects,expected",
    [
        (frozenset({AspectID.LIGHT}), Polarity.POSITIVE),
        (frozenset({AspectID.VOID, AspectID.DECAY}), Polarity.NEGATIVE),
        (frozenset({AspectID.VOID, AspectID.FORM}), Polarity.NEUTRAL),
    ],
)
def test_sigil_polarity_derived(aspects, expected):
    s = Sigil(
        name="x",
        aspects=aspects,
        effect_class=EffectClass.COGNITION,
        resonance_ceiling=0.2,
        contradiction_severity=ContradictionSeverity.SOFT,
    )
    assert s.polarity == expected


def test_sigil_raises_on_mismatched_fingerprint():
    aspects = frozenset({AspectID.FORM})
    with pytest.raises(ValueError, match="semantic_fingerprint"):
        Sigil(
            name="n",
            aspects=aspects,
            effect_class=EffectClass.BINDING,
            resonance_ceiling=1.0,
            contradiction_severity=ContradictionSeverity.HARD,
            semantic_fingerprint="0" * 64,
        )


def test_sigil_frozen_rejects_mutation():
    s = Sigil(
        name="n",
        aspects=frozenset({AspectID.FORM}),
        effect_class=EffectClass.BINDING,
        resonance_ceiling=1.0,
        contradiction_severity=ContradictionSeverity.HARD,
    )
    with pytest.raises(ValidationError):
        s.name = "other"


def _zero_semantic_vector() -> SemanticVector:
    return SemanticVector(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))


def _minimal_intent_vector() -> IntentVector:
    z = _zero_semantic_vector()
    return IntentVector(
        vector=z,
        projection_method=ProjectionMethod.FULL,
        constraint_component=z,
        semantic_component=z,
        confidence=1.0,
    )


def _minimal_verdict() -> Verdict:
    return Verdict(
        verdict_type=VerdictType.COHERENT,
        resonance=ResonanceScore(
            raw=0.5,
            adjusted=0.5,
            ceiling_applied=False,
            proof="Test proof sentence for resonance score.",
        ),
        effect_description="desc",
        incoherence_reason=None,
        casting_note="note",
        intent_vector=_minimal_intent_vector(),
    )


def test_intent_rejects_long_objective():
    with pytest.raises(ValidationError):
        Intent(
            objective="x" * 501,
            scope="ok",
            reversibility=ReversibilityClass.IRREVERSIBLE,
            side_effect_tolerance=SideEffectTolerance.HIGH,
        )


@pytest.mark.parametrize("field", ["raw", "adjusted"])
def test_resonance_score_rejects_out_of_range(field):
    kwargs = {
        "raw": 0.5,
        "adjusted": 0.5,
        "ceiling_applied": True,
        "proof": "p",
    }
    kwargs[field] = 1.01
    with pytest.raises(ValidationError):
        ResonanceScore(**kwargs)
    kwargs[field] = -0.01
    with pytest.raises(ValidationError):
        ResonanceScore(**kwargs)


def test_lineage_auto_generates_branch_id():
    lin = Lineage(parent_cast_id="parent-ulid", depth=1)
    assert isinstance(lin.branch_id, str) and len(lin.branch_id) >= 20


def test_glyph_seed_auto_generates_seed_id_and_vector():
    pattern = frozenset({AspectID.MIND, AspectID.VOID})
    g = GlyphSeed(aspect_pattern=pattern)
    assert g.seed_id
    assert g.semantic_vector.components == SemanticVector.from_aspects(pattern).components


def test_glyph_seed_rejects_supplied_seed_id():
    with pytest.raises(ValueError, match="seed_id"):
        GlyphSeed.model_validate(
            {
                "seed_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "aspect_pattern": frozenset({AspectID.FORM}),
            }
        )


def test_semantic_query_proximity_threshold_requires_vector():
    with pytest.raises(ValueError, match="proximity_to"):
        SemanticQuery(proximity_threshold=0.5)


def test_cast_result_auto_fields_and_rejects_supplied():
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    sigil = Sigil(
        name="n",
        aspects=frozenset({AspectID.FORM}),
        effect_class=EffectClass.BINDING,
        resonance_ceiling=1.0,
        contradiction_severity=ContradictionSeverity.HARD,
    )
    v = _minimal_verdict()
    cr = CastResult(intent=intent, sigil=sigil, verdict=v)
    assert cr.immutable is True
    assert cr.cast_id
    assert cr.timestamp.tzinfo == timezone.utc

    with pytest.raises(ValueError, match="cast_id"):
        CastResult.model_validate(
            {"cast_id": "x", "intent": intent, "sigil": sigil, "verdict": v}
        )
    with pytest.raises(ValueError, match="timestamp"):
        CastResult.model_validate(
            {
                "timestamp": datetime.now(timezone.utc),
                "intent": intent,
                "sigil": sigil,
                "verdict": v,
            }
        )
    with pytest.raises(ValueError, match="immutable"):
        CastResult.model_validate(
            {"immutable": True, "intent": intent, "sigil": sigil, "verdict": v}
        )


def test_cast_result_frozen_rejects_mutation():
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    sigil = Sigil(
        name="n",
        aspects=frozenset({AspectID.FORM}),
        effect_class=EffectClass.BINDING,
        resonance_ceiling=1.0,
        contradiction_severity=ContradictionSeverity.HARD,
    )
    cr = CastResult(intent=intent, sigil=sigil, verdict=_minimal_verdict())
    with pytest.raises(ValueError, match="mutat"):
        cr.intent = intent


def test_cast_result_accepts_lineage_and_glyph_seed_id():
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
        resonance_ceiling=0.0,
        contradiction_severity=ContradictionSeverity.NONE,
    )
    lin = Lineage(parent_cast_id="p", depth=2, branch_id="01ARZ3NDEKTSV4RRFFQ69G5FAV")
    cr = CastResult(
        intent=intent,
        sigil=sigil,
        verdict=_minimal_verdict(),
        lineage=lin,
        glyph_seed_id="seed-ref",
    )
    assert cr.lineage is lin
    assert cr.glyph_seed_id == "seed-ref"


def test_cast_result_sequential_instances_differ_ids_and_timestamps():
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    sigil = Sigil(
        name="n",
        aspects=frozenset({AspectID.FORM}),
        effect_class=EffectClass.BINDING,
        resonance_ceiling=1.0,
        contradiction_severity=ContradictionSeverity.HARD,
    )
    v = _minimal_verdict()
    c1 = CastResult(intent=intent, sigil=sigil, verdict=v)
    time.sleep(0.002)
    c2 = CastResult(intent=intent, sigil=sigil, verdict=v)
    assert c1.cast_id != c2.cast_id
    assert c1.timestamp != c2.timestamp


def test_projection_method_has_full_and_partial():
    assert len(ProjectionMethod) == 2
    assert ProjectionMethod.FULL.value == "FULL"
    assert ProjectionMethod.PARTIAL.value == "PARTIAL"


def test_intent_vector_importable():
    assert IntentVector is not None


def test_intent_vector_full_requires_semantic_component():
    z = _zero_semantic_vector()
    with pytest.raises(ValueError, match="semantic_component"):
        IntentVector(
            vector=z,
            projection_method=ProjectionMethod.FULL,
            constraint_component=z,
            semantic_component=None,
            confidence=1.0,
        )


def test_intent_vector_partial_confidence_must_not_exceed_065():
    z = _zero_semantic_vector()
    with pytest.raises(ValueError, match="confidence"):
        IntentVector(
            vector=z,
            projection_method=ProjectionMethod.PARTIAL,
            constraint_component=z,
            semantic_component=None,
            confidence=0.90,
        )


def test_intent_vector_full_with_semantic_component_ok():
    z = _zero_semantic_vector()
    iv = IntentVector(
        vector=z,
        projection_method=ProjectionMethod.FULL,
        constraint_component=z,
        semantic_component=z,
        confidence=1.0,
    )
    assert iv.projection_method == ProjectionMethod.FULL
    assert iv.semantic_component is not None


def test_intent_vector_partial_semantic_none_confidence_060_ok():
    z = _zero_semantic_vector()
    iv = IntentVector(
        vector=z,
        projection_method=ProjectionMethod.PARTIAL,
        constraint_component=z,
        semantic_component=None,
        confidence=0.60,
    )
    assert iv.semantic_component is None
    assert iv.confidence == 0.60


def test_intent_vector_frozen_rejects_mutation():
    iv = _minimal_intent_vector()
    with pytest.raises(ValidationError):
        iv.confidence = 0.5


def test_verdict_requires_intent_vector():
    with pytest.raises(ValidationError):
        Verdict(
            verdict_type=VerdictType.COHERENT,
            resonance=ResonanceScore(
                raw=0.5,
                adjusted=0.5,
                ceiling_applied=False,
                proof="Test proof sentence for resonance score.",
            ),
            effect_description="desc",
            incoherence_reason=None,
            casting_note="note",
        )


def test_verdict_with_valid_intent_vector_ok():
    v = _minimal_verdict()
    assert v.intent_vector.projection_method == ProjectionMethod.FULL
    assert v.intent_vector.confidence == 1.0
