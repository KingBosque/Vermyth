from __future__ import annotations

import math
from typing import Optional

from vermyth.registry import AspectRegistry
from vermyth.schema import (
    ContradictionSeverity,
    FluidSigil,
    Intent,
    IntentVector,
    ProjectionMethod,
    SemanticVector,
    Sigil,
    Verdict,
)


def build_constraint_vector(engine, intent: Intent) -> SemanticVector:
    from vermyth.engine.resonance import _REVERSIBILITY_PRESSURES, _SIDE_EFFECT_PRESSURES

    dim = AspectRegistry.get().dimensionality
    acc = [0.0 for _ in range(dim)]
    rev6 = _REVERSIBILITY_PRESSURES[intent.reversibility]
    side6 = _SIDE_EFFECT_PRESSURES[intent.side_effect_tolerance]
    rev = tuple(rev6) + tuple(0.0 for _ in range(max(0, dim - len(rev6))))
    side = tuple(side6) + tuple(0.0 for _ in range(max(0, dim - len(side6))))
    for i in range(dim):
        acc[i] = engine._clip_component(rev[i] + side[i])
    return engine._normalize_unit(tuple(acc))


def clip_component(x: float) -> float:
    if x > 1.0:
        return 1.0
    if x < -1.0:
        return -1.0
    return x


def normalize_unit(components: tuple[float, ...]) -> SemanticVector:
    basis_version = AspectRegistry.get().current_basis_version()
    s = sum(c * c for c in components)
    norm = math.sqrt(s)
    if norm == 0.0:
        return SemanticVector(
            components=tuple(0.0 for _ in components),
            basis_version=basis_version,
        )
    t = tuple(c / norm for c in components)
    return SemanticVector(components=t, basis_version=basis_version)


def build_semantic_vector(engine, intent: Intent) -> Optional[SemanticVector]:
    from vermyth.engine.resonance import _log_stderr

    if engine.backend is None:
        return None
    try:
        raw_list = engine.backend.project(intent.objective, intent.scope)
    except BaseException as exc:
        _log_stderr(f"[vermyth] projection backend failed: {exc!r}")
        return None
    if not isinstance(raw_list, list) or len(raw_list) < 6:
        _log_stderr("[vermyth] projection backend failed: invalid list length")
        return None
    floats: list[float] = []
    for x in raw_list:
        if not isinstance(x, (int, float)):
            _log_stderr("[vermyth] projection backend failed: non-numeric component")
            return None
        xf = float(x)
        if xf < -1.0 or xf > 1.0:
            _log_stderr("[vermyth] projection backend failed: component out of range")
            return None
        floats.append(xf)
    dim = AspectRegistry.get().dimensionality
    if len(floats) < dim:
        floats.extend(0.0 for _ in range(dim - len(floats)))
    s = sum(f * f for f in floats)
    norm = math.sqrt(s)
    if norm == 0.0:
        return SemanticVector(
            components=tuple(0.0 for _ in floats),
            basis_version=AspectRegistry.get().current_basis_version(),
        )
    t = tuple(f / norm for f in floats)
    return SemanticVector(
        components=t,
        basis_version=AspectRegistry.get().current_basis_version(),
    )


def combine_vectors(
    engine, constraint: SemanticVector, semantic: Optional[SemanticVector]
) -> tuple[SemanticVector, ProjectionMethod, float]:
    _ = engine
    if semantic is None:
        return (constraint, ProjectionMethod.PARTIAL, 0.60)
    dim = len(constraint.components)
    combined: list[float] = []
    for i in range(dim):
        s = semantic.components[i] if i < len(semantic.components) else 0.0
        combined.append(constraint.components[i] * 0.35 + s * 0.65)
    combined_t = tuple(combined)
    s = sum(c * c for c in combined_t)
    norm = math.sqrt(s)
    if norm == 0.0:
        return (constraint, ProjectionMethod.PARTIAL, 0.60)
    t = tuple(c / norm for c in combined_t)
    vec = SemanticVector(components=t)
    return (vec, ProjectionMethod.FULL, 1.0)


def build_intent_vector(engine, intent: Intent) -> IntentVector:
    constraint = build_constraint_vector(engine, intent)
    semantic = build_semantic_vector(engine, intent)
    combined, method, confidence = combine_vectors(engine, constraint, semantic)
    return IntentVector(
        vector=combined,
        projection_method=method,
        constraint_component=constraint,
        semantic_component=semantic,
        confidence=confidence,
    )


def evaluate_with_intent_vector(
    engine, sigil: Sigil | FluidSigil, intent: Intent, intent_vector: IntentVector
) -> Verdict:
    resonance, cosine = engine._compute_resonance(sigil, intent_vector)
    vt = engine._verdict_type(resonance.adjusted)
    casting = engine._casting_note(sigil, vt, intent_vector)
    incoh = engine._incoherence_reason(sigil, vt, cosine)
    effect_desc = engine._effect_description(sigil, vt)
    return Verdict(
        verdict_type=vt,
        resonance=resonance,
        effect_description=effect_desc,
        incoherence_reason=incoh,
        casting_note=casting,
        intent_vector=intent_vector,
    )


def alignment_word(cosine: float) -> str:
    if cosine >= 0.70:
        return "strongly"
    if cosine >= 0.40:
        return "moderately"
    if cosine >= 0.10:
        return "weakly"
    return "opposingly"


def penalty_phrase(severity: ContradictionSeverity) -> str:
    if severity == ContradictionSeverity.HARD:
        return "HARD contradiction penalised -0.40"
    if severity == ContradictionSeverity.SOFT:
        return "SOFT contradiction penalised -0.18"
    return "no contradiction penalty"
