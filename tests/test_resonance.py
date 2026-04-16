from pathlib import Path

import pytest

from vermyth.contracts import EvaluationContract, ProjectionBackend
from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine, _CASTING_NOTES
from vermyth.schema import (
    AspectID,
    CastResult,
    EffectClass,
    GlyphSeed,
    Intent,
    ReversibilityClass,
    SideEffectTolerance,
    VerdictType,
)


class MockBackend(ProjectionBackend):
    def project(self, objective: str, scope: str) -> list[float]:
        return [0.1, 0.8, 0.2, 0.6, -0.1, 0.9]


@pytest.fixture
def composition() -> CompositionEngine:
    return CompositionEngine()


def test_resonance_engine_importable():
    from vermyth.engine.resonance import ResonanceEngine as RE

    assert RE is ResonanceEngine


def test_resonance_engine_subclass_engine_contract():
    assert issubclass(ResonanceEngine, EvaluationContract)


def test_cast_composes_and_evaluates(composition):
    eng = ResonanceEngine(composition)
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    cr = eng.cast(frozenset({AspectID.FORM}), intent)
    assert cr.sigil.aspects == frozenset({AspectID.FORM})
    assert cr.verdict.verdict_type in {
        VerdictType.COHERENT,
        VerdictType.PARTIAL,
        VerdictType.INCOHERENT,
    }


def test_casting_notes_has_36_entries():
    assert len(_CASTING_NOTES) == 36


def test_evaluate_mind_light_coherent_with_mock(composition):
    sigil = composition.compose(frozenset({AspectID.MIND, AspectID.LIGHT}))

    class AlignedMock(ProjectionBackend):
        def project(self, objective: str, scope: str) -> list[float]:
            return [float(x) for x in sigil.semantic_vector.components]

    eng = ResonanceEngine(composition, AlignedMock())
    intent = Intent(
        objective="align",
        scope="bind",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )
    v = eng.evaluate(sigil, intent)
    assert v.verdict_type == VerdictType.COHERENT


def test_evaluate_void_mind_not_coherent_due_to_hard_penalty(composition):
    eng = ResonanceEngine(composition, MockBackend())
    sigil = composition.compose(frozenset({AspectID.VOID, AspectID.MIND}))
    intent = Intent(
        objective="x",
        scope="y",
        reversibility=ReversibilityClass.PARTIAL,
        side_effect_tolerance=SideEffectTolerance.MEDIUM,
    )
    v = eng.evaluate(sigil, intent)
    assert v.verdict_type != VerdictType.COHERENT


def test_evaluate_never_raises(composition):
    eng = ResonanceEngine(composition, MockBackend())
    sigil = composition.compose(frozenset({AspectID.VOID, AspectID.DECAY}))
    intent = Intent(
        objective="",
        scope="",
        reversibility=ReversibilityClass.IRREVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.NONE,
    )
    v = eng.evaluate(sigil, intent)
    assert v.verdict_type in {
        VerdictType.COHERENT,
        VerdictType.PARTIAL,
        VerdictType.INCOHERENT,
    }
    assert 0.0 <= float(v.resonance.raw) <= 1.0
    assert 0.0 <= float(v.resonance.adjusted) <= 1.0


def test_evaluate_intent_vector_present(composition):
    eng = ResonanceEngine(composition, MockBackend())
    sigil = composition.compose(frozenset({AspectID.FORM}))
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    v = eng.evaluate(sigil, intent)
    assert v.intent_vector is not None


def test_evaluate_no_backend_partial_projection(composition):
    eng = ResonanceEngine(composition, None)
    sigil = composition.compose(frozenset({AspectID.LIGHT}))
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.PARTIAL,
        side_effect_tolerance=SideEffectTolerance.MEDIUM,
    )
    v = eng.evaluate(sigil, intent)
    from vermyth.schema import ProjectionMethod

    assert v.intent_vector.projection_method == ProjectionMethod.PARTIAL


def test_evaluate_mock_backend_full_projection(composition):
    eng = ResonanceEngine(composition, MockBackend())
    sigil = composition.compose(frozenset({AspectID.LIGHT}))
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.PARTIAL,
        side_effect_tolerance=SideEffectTolerance.MEDIUM,
    )
    v = eng.evaluate(sigil, intent)
    from vermyth.schema import ProjectionMethod

    assert v.intent_vector.projection_method == ProjectionMethod.FULL


def test_evaluate_proof_contains_sigil_name(composition):
    eng = ResonanceEngine(composition, MockBackend())
    sigil = composition.compose(frozenset({AspectID.MOTION}))
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )
    v = eng.evaluate(sigil, intent)
    assert sigil.name in v.resonance.proof


def test_cast_frozen_cast_result(composition):
    eng = ResonanceEngine(composition, MockBackend())
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    cr = eng.cast(frozenset({AspectID.FORM}), intent)
    assert cr.cast_id
    assert cr.lineage is None

    with pytest.raises(ValueError, match="mutat"):
        cr.cast_id = "x"


def test_accumulate_new_seed(composition):
    eng = ResonanceEngine(composition, MockBackend())
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    cr = eng.cast(frozenset({AspectID.FORM}), intent)
    seed = eng.accumulate(cr, [])
    assert seed is not None
    assert seed.observed_count == 1


def test_accumulate_incoherent_no_seed_returns_none(composition):
    eng = ResonanceEngine(composition, None)
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.IRREVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.NONE,
    )
    aspects = frozenset({AspectID.VOID, AspectID.MIND})
    sigil = composition.compose(aspects)
    from vermyth.schema import ResonanceScore, Verdict, VerdictType

    v = Verdict(
        verdict_type=VerdictType.INCOHERENT,
        resonance=ResonanceScore(
            raw=0.1,
            adjusted=0.1,
            ceiling_applied=False,
            proof="Forced low resonance for accumulate test.",
        ),
        effect_description="x",
        incoherence_reason="y",
        casting_note="z",
        intent_vector=eng.evaluate(sigil, intent).intent_vector,
    )
    cr = CastResult(intent=intent, sigil=sigil, verdict=v)
    assert eng.accumulate(cr, []) is None


def test_accumulate_twice_same_pattern_observed_count_two(composition):
    eng = ResonanceEngine(composition, MockBackend())
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )
    aspects = frozenset({AspectID.MIND, AspectID.LIGHT})
    cr1 = eng.cast(aspects, intent)
    s1 = eng.accumulate(cr1, [])
    cr2 = eng.cast(aspects, intent)
    s2 = eng.accumulate(cr2, [s1])
    assert s2.observed_count == 2


def test_accumulate_running_mean_after_two_calls(composition):
    eng = ResonanceEngine(composition, MockBackend())
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )
    aspects = frozenset({AspectID.FORM})
    cr1 = eng.cast(aspects, intent)
    a1 = cr1.verdict.resonance.adjusted
    s1 = eng.accumulate(cr1, [])
    cr2 = eng.cast(aspects, intent)
    a2 = cr2.verdict.resonance.adjusted
    s2 = eng.accumulate(cr2, [s1])
    expected = (a1 + a2) / 2.0
    assert s2.mean_resonance == pytest.approx(expected)


def test_crystallize_none_when_observed_low(composition):
    eng = ResonanceEngine(composition, MockBackend())
    g = GlyphSeed(
        aspect_pattern=frozenset({AspectID.FORM}),
        observed_count=3,
        mean_resonance=0.9,
        coherence_rate=0.9,
        candidate_effect_class=EffectClass.MANIFESTATION,
    )
    assert eng.crystallize(g) is None


def test_crystallize_returns_glyph_prefixed_sigil(composition):
    eng = ResonanceEngine(composition, MockBackend())
    g = GlyphSeed(
        aspect_pattern=frozenset({AspectID.MIND, AspectID.LIGHT}),
        observed_count=10,
        mean_resonance=0.85,
        coherence_rate=0.70,
        candidate_effect_class=EffectClass.BINDING,
    )
    s = eng.crystallize(g)
    assert s is not None
    assert s.name.startswith("Glyph:")
    base = composition.compose(g.aspect_pattern)
    assert s.name == f"Glyph:{base.name}"


def test_crystallize_sigil_aspects_match_seed(composition):
    eng = ResonanceEngine(composition, MockBackend())
    pattern = frozenset({AspectID.MIND, AspectID.LIGHT})
    g = GlyphSeed(
        aspect_pattern=pattern,
        observed_count=10,
        mean_resonance=0.85,
        coherence_rate=0.70,
        candidate_effect_class=EffectClass.BINDING,
    )
    s = eng.crystallize(g)
    assert s is not None
    assert s.aspects == pattern
