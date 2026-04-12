import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from vermyth.contracts import EngineContract
from vermyth.engine.composition import CompositionEngine
from vermyth.schema import ASPECT_CANONICAL_ORDER, AspectID, SemanticVector


def _sigils_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "vermyth" / "data" / "sigils"


def _canonical_aspect_sets() -> list[frozenset[AspectID]]:
    out: list[frozenset[AspectID]] = []
    for fname in (
        "canonical_single.json",
        "canonical_dual.json",
        "canonical_triple.json",
    ):
        path = _sigils_dir() / fname
        with path.open(encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            names = entry["aspects"]
            out.append(frozenset(AspectID[n] for n in names))
    return out


def test_composition_engine_importable():
    from vermyth.engine.composition import CompositionEngine as CE

    assert CE is CompositionEngine


def test_composition_engine_subclass_of_engine_contract():
    assert issubclass(CompositionEngine, EngineContract)


@pytest.mark.parametrize(
    "aspect,expected_name",
    [
        (AspectID.VOID, "Nullform"),
        (AspectID.FORM, "Solidus"),
        (AspectID.MOTION, "Kineval"),
        (AspectID.MIND, "Ideoglyph"),
        (AspectID.DECAY, "Solvite"),
        (AspectID.LIGHT, "Verite"),
    ],
)
def test_compose_single_aspect_name(aspect, expected_name):
    eng = CompositionEngine()
    s = eng.compose(frozenset({aspect}))
    assert s.name == expected_name


def test_compose_dual_veritas_bind():
    eng = CompositionEngine()
    s = eng.compose(frozenset({AspectID.MIND, AspectID.LIGHT}))
    assert s.name == "Veritas Bind"


def test_compose_triple_golemancer():
    eng = CompositionEngine()
    s = eng.compose(
        frozenset({AspectID.FORM, AspectID.MOTION, AspectID.MIND})
    )
    assert s.name == "Golemancer"


def test_compose_semantic_fingerprint_nonempty():
    eng = CompositionEngine()
    s = eng.compose(frozenset({AspectID.FORM}))
    assert s.semantic_fingerprint


def test_compose_semantic_vector_matches_manual():
    eng = CompositionEngine()
    aspects = frozenset({AspectID.MOTION, AspectID.DECAY})
    s = eng.compose(aspects)
    assert s.semantic_vector.components == SemanticVector.from_aspects(
        aspects
    ).components


def test_compose_void_mind_contradiction_hard():
    eng = CompositionEngine()
    s = eng.compose(frozenset({AspectID.VOID, AspectID.MIND}))
    from vermyth.schema import ContradictionSeverity

    assert s.contradiction_severity == ContradictionSeverity.HARD


def test_compose_form_motion_contradiction_none():
    eng = CompositionEngine()
    s = eng.compose(frozenset({AspectID.FORM, AspectID.MOTION}))
    from vermyth.schema import ContradictionSeverity

    assert s.contradiction_severity == ContradictionSeverity.NONE


def test_compose_empty_raises():
    eng = CompositionEngine()
    with pytest.raises(ValueError, match="at least one"):
        eng.compose(frozenset())


def test_compose_four_aspects_raises():
    eng = CompositionEngine()
    four = frozenset(
        {
            AspectID.VOID,
            AspectID.FORM,
            AspectID.MOTION,
            AspectID.MIND,
        }
    )
    with pytest.raises(ValueError, match="at most three"):
        eng.compose(four)


def test_compose_sigil_frozen():
    eng = CompositionEngine()
    s = eng.compose(frozenset({AspectID.LIGHT}))
    with pytest.raises(ValidationError):
        s.name = "x"


def test_extended_dir_empty_loads():
    CompositionEngine()


def test_compose_identical_aspects_identical_fingerprint():
    eng = CompositionEngine()
    a = frozenset({AspectID.VOID, AspectID.LIGHT})
    s1 = eng.compose(a)
    s2 = eng.compose(a)
    assert s1.semantic_fingerprint == s2.semantic_fingerprint


@pytest.mark.parametrize(
    "aspects",
    _canonical_aspect_sets(),
    ids=lambda a: "+".join(x.name for x in sorted(a, key=lambda x: ASPECT_CANONICAL_ORDER.index(x))),
)
def test_all_canonical_combinations_resolve(aspects):
    eng = CompositionEngine()
    eng.compose(aspects)


def test_unimplemented_engine_methods_raise():
    eng = CompositionEngine()
    from vermyth.schema import (
        CastResult,
        GlyphSeed,
        Intent,
        IntentVector,
        ProjectionMethod,
        ReversibilityClass,
        SideEffectTolerance,
        Sigil,
        Verdict,
        VerdictType,
        ResonanceScore,
        SemanticVector,
    )

    sigil = eng.compose(frozenset({AspectID.FORM}))
    intent = Intent(
        objective="o",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    with pytest.raises(NotImplementedError):
        eng.evaluate(sigil, intent)
    with pytest.raises(NotImplementedError):
        eng.cast(frozenset({AspectID.FORM}), intent)

    zvec = SemanticVector(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    v = Verdict(
        verdict_type=VerdictType.COHERENT,
        resonance=ResonanceScore(
            raw=0.5,
            adjusted=0.5,
            ceiling_applied=False,
            proof="p",
        ),
        effect_description="d",
        incoherence_reason=None,
        casting_note="n",
        intent_vector=IntentVector(
            vector=zvec,
            projection_method=ProjectionMethod.FULL,
            constraint_component=zvec,
            semantic_component=zvec,
            confidence=1.0,
        ),
    )
    cr = CastResult(intent=intent, sigil=sigil, verdict=v)
    with pytest.raises(NotImplementedError):
        eng.accumulate(cr, [])
    seed = GlyphSeed(aspect_pattern=frozenset({AspectID.FORM}))
    with pytest.raises(NotImplementedError):
        eng.crystallize(seed)
