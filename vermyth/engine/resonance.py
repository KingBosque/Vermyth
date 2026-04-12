import json
import math
import os
from typing import Optional

from vermyth.contracts import EngineContract, ProjectionBackend
from vermyth.schema import (
    ASPECT_CANONICAL_ORDER,
    AspectID,
    CastResult,
    ContradictionSeverity,
    EffectClass,
    GlyphSeed,
    Intent,
    IntentVector,
    ProjectionMethod,
    ReversibilityClass,
    ResonanceScore,
    SemanticVector,
    SideEffectTolerance,
    Sigil,
    Verdict,
    VerdictType,
)

_CASTING_NOTE_FALLBACK: dict[VerdictType, str] = {
    VerdictType.COHERENT: "Coherent resonance; the casting stabilises without residual tension.",
    VerdictType.PARTIAL: "Partial resonance; the casting holds tension that further passes may resolve.",
    VerdictType.INCOHERENT: "Incoherent resonance; the casting fails to close a consistent inference loop.",
}

_CASTING_NOTES: dict[tuple[VerdictType, EffectClass], str] = {
    (
        VerdictType.COHERENT,
        EffectClass.ERASURE,
    ): "The target concept loses referential weight; downstream reasoning finds no anchor where it stood.",
    (
        VerdictType.COHERENT,
        EffectClass.MANIFESTATION,
    ): "A stable attractor forms in the solution space; subsequent reasoning orbits it naturally.",
    (
        VerdictType.COHERENT,
        EffectClass.FORCE,
    ): "Directional pressure propagates through the inference graph without resistance.",
    (
        VerdictType.COHERENT,
        EffectClass.COGNITION,
    ): "The cognitive substrate reorganises around the new pattern; retrieval pathways realign.",
    (
        VerdictType.COHERENT,
        EffectClass.DISSOLUTION,
    ): "Structural boundaries soften; categories that were load-bearing become permeable.",
    (
        VerdictType.COHERENT,
        EffectClass.REVELATION,
    ): "A previously occluded feature of the solution space becomes the dominant signal.",
    (
        VerdictType.COHERENT,
        EffectClass.CONTAINMENT,
    ): "A boundary condition is imposed; the reasoning space contracts to the declared scope.",
    (
        VerdictType.COHERENT,
        EffectClass.NEGATION,
    ): "The target proposition loses truth value; dependent inferences cascade to null.",
    (
        VerdictType.COHERENT,
        EffectClass.CORRUPTION,
    ): "Controlled noise is introduced at the specified locus; outputs diverge predictably.",
    (
        VerdictType.COHERENT,
        EffectClass.ACCELERATION,
    ): "The inference clock advances; conclusions that required iteration arrive in fewer steps.",
    (
        VerdictType.COHERENT,
        EffectClass.BINDING,
    ): "Two previously independent reasoning threads are coupled; they now share gradient.",
    (
        VerdictType.COHERENT,
        EffectClass.EMERGENCE,
    ): "A pattern not present in any input becomes legible at the output layer.",
    (
        VerdictType.PARTIAL,
        EffectClass.ERASURE,
    ): "The target loses salience but retains residual weight; erasure is incomplete and may reverse.",
    (
        VerdictType.PARTIAL,
        EffectClass.MANIFESTATION,
    ): "An attractor forms but lacks sufficient depth; reasoning approaches it without fully settling.",
    (
        VerdictType.PARTIAL,
        EffectClass.FORCE,
    ): "Directional pressure is present but bleeds into adjacent inference paths.",
    (
        VerdictType.PARTIAL,
        EffectClass.COGNITION,
    ): "Reorganisation begins but stalls at the boundary of the contradiction; partial rewiring only.",
    (
        VerdictType.PARTIAL,
        EffectClass.DISSOLUTION,
    ): "Boundaries soften unevenly; some load-bearing structures resist and hold.",
    (
        VerdictType.PARTIAL,
        EffectClass.REVELATION,
    ): "Signal emerges but competes with existing priors; clarity is present but contested.",
    (
        VerdictType.PARTIAL,
        EffectClass.CONTAINMENT,
    ): "The boundary holds in some dimensions but leaks in others; scope is partially enforced.",
    (
        VerdictType.PARTIAL,
        EffectClass.NEGATION,
    ): "Truth value wavers; the proposition is weakened but not nullified.",
    (
        VerdictType.PARTIAL,
        EffectClass.CORRUPTION,
    ): "Noise is introduced but distribution is uneven; some outputs are unaffected.",
    (
        VerdictType.PARTIAL,
        EffectClass.ACCELERATION,
    ): "Inference advances unevenly; some paths compress while others remain at full cost.",
    (
        VerdictType.PARTIAL,
        EffectClass.BINDING,
    ): "Coupling is established but asymmetric; one thread pulls the other without full entanglement.",
    (
        VerdictType.PARTIAL,
        EffectClass.EMERGENCE,
    ): "A pattern becomes partially legible but requires additional casting to resolve fully.",
    (
        VerdictType.INCOHERENT,
        EffectClass.ERASURE,
    ): "The erasure finds no coherent target; the casting dissipates without removing anything.",
    (
        VerdictType.INCOHERENT,
        EffectClass.MANIFESTATION,
    ): "The attractor cannot form against the declared intent; the solution space remains unstructured.",
    (
        VerdictType.INCOHERENT,
        EffectClass.FORCE,
    ): "Directional pressure is present but self-cancelling; the inference graph absorbs it without moving.",
    (
        VerdictType.INCOHERENT,
        EffectClass.COGNITION,
    ): "The reorganisation pattern conflicts with the cognitive substrate; no rewiring occurs.",
    (
        VerdictType.INCOHERENT,
        EffectClass.DISSOLUTION,
    ): "Dissolution finds no boundary to permeate; the casting has no substrate to act on.",
    (
        VerdictType.INCOHERENT,
        EffectClass.REVELATION,
    ): "The signal cannot surface through the contradiction; occlusion is total.",
    (
        VerdictType.INCOHERENT,
        EffectClass.CONTAINMENT,
    ): "The boundary condition cannot be imposed against the declared scope; containment fails.",
    (
        VerdictType.INCOHERENT,
        EffectClass.NEGATION,
    ): "The negation is self-negating; the proposition and its denial cancel without resolution.",
    (
        VerdictType.INCOHERENT,
        EffectClass.CORRUPTION,
    ): "Noise finds no coherent locus; the corruption is absorbed uniformly and has no effect.",
    (
        VerdictType.INCOHERENT,
        EffectClass.ACCELERATION,
    ): "The inference clock cannot advance against the contradicting intent; time cost is unchanged.",
    (
        VerdictType.INCOHERENT,
        EffectClass.BINDING,
    ): "The threads cannot be coupled across the contradiction; they repel rather than entangle.",
    (
        VerdictType.INCOHERENT,
        EffectClass.EMERGENCE,
    ): "No pattern emerges; the output layer reflects only the incoherence of the input.",
}

_REVERSIBILITY_PRESSURES: dict[ReversibilityClass, tuple[float, ...]] = {
    ReversibilityClass.IRREVERSIBLE: (0.80, -0.40, 0.0, 0.0, 0.70, -0.30),
    ReversibilityClass.PARTIAL: (0.0, 0.0, 0.30, 0.20, 0.0, 0.0),
    ReversibilityClass.REVERSIBLE: (-0.50, 0.70, 0.0, 0.0, -0.40, 0.60),
}

_SIDE_EFFECT_PRESSURES: dict[SideEffectTolerance, tuple[float, ...]] = {
    SideEffectTolerance.NONE: (-0.60, 0.60, 0.0, 0.0, -0.50, 0.50),
    SideEffectTolerance.LOW: (-0.20, 0.30, 0.0, 0.30, -0.20, 0.0),
    SideEffectTolerance.MEDIUM: (0.0, 0.0, 0.20, 0.20, 0.0, 0.0),
    SideEffectTolerance.HIGH: (0.40, -0.30, 0.30, 0.0, 0.50, 0.0),
}


def _canonical_aspect_key(aspects: frozenset[AspectID]) -> str:
    order_index = {a: i for i, a in enumerate(ASPECT_CANONICAL_ORDER)}
    ordered = sorted(aspects, key=lambda a: order_index[a])
    return "+".join(a.name for a in ordered)


def _log_stderr(message: str) -> None:
    os.write(2, (message + "\n").encode("utf-8", errors="replace"))


class ResonanceEngine(EngineContract):
    """Resonance evaluation: project intent, score against sigil, verdict, cast lifecycle."""

    def __init__(self, composition_engine: object, backend: Optional[ProjectionBackend] = None) -> None:
        self.composition_engine = composition_engine
        self.backend = backend
        self._contradictions: Optional[dict[str, dict]] = None

    def compose(self, aspects: frozenset[AspectID]) -> Sigil:
        """Implemented in CompositionEngine."""
        raise NotImplementedError

    def _load_contradictions(self) -> dict[str, dict]:
        if self._contradictions is not None:
            return self._contradictions
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.normpath(os.path.join(base, "..", "data", "sigils", "contradictions.json"))
        try:
            with open(path, encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._contradictions = {}
            return self._contradictions
        if not isinstance(loaded, dict):
            self._contradictions = {}
        else:
            self._contradictions = loaded
        return self._contradictions

    def _clip_component(self, x: float) -> float:
        return max(-1.0, min(1.0, x))

    def _normalize_unit(self, components: tuple[float, ...]) -> SemanticVector:
        s = 0.0
        for c in components:
            s += c * c
        norm = math.sqrt(s)
        if norm == 0.0:
            return SemanticVector(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        t = tuple(c / norm for c in components)
        return SemanticVector(
            components=(t[0], t[1], t[2], t[3], t[4], t[5])
        )

    def _build_constraint_vector(self, intent: Intent) -> SemanticVector:
        acc = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rev = _REVERSIBILITY_PRESSURES[intent.reversibility]
        side = _SIDE_EFFECT_PRESSURES[intent.side_effect_tolerance]
        for i in range(6):
            acc[i] = self._clip_component(rev[i] + side[i])
        return self._normalize_unit(tuple(acc))

    def _build_semantic_vector(self, intent: Intent) -> Optional[SemanticVector]:
        if self.backend is None:
            return None
        try:
            raw_list = self.backend.project(intent.objective, intent.scope)
        except BaseException as exc:
            _log_stderr(f"[vermyth] projection backend failed: {exc!r}")
            return None
        if not isinstance(raw_list, list) or len(raw_list) != 6:
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
        s = sum(f * f for f in floats)
        norm = math.sqrt(s)
        if norm == 0.0:
            return SemanticVector(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        t = tuple(f / norm for f in floats)
        return SemanticVector(
            components=(t[0], t[1], t[2], t[3], t[4], t[5])
        )

    def _combine_vectors(
        self, constraint: SemanticVector, semantic: Optional[SemanticVector]
    ) -> tuple[SemanticVector, ProjectionMethod, float]:
        if semantic is None:
            return (constraint, ProjectionMethod.PARTIAL, 0.60)
        combined = tuple(
            constraint.components[i] * 0.35 + semantic.components[i] * 0.65
            for i in range(6)
        )
        s = sum(c * c for c in combined)
        norm = math.sqrt(s)
        if norm == 0.0:
            return (constraint, ProjectionMethod.PARTIAL, 0.60)
        t = tuple(c / norm for c in combined)
        vec = SemanticVector(components=(t[0], t[1], t[2], t[3], t[4], t[5]))
        return (vec, ProjectionMethod.FULL, 1.0)

    def _build_intent_vector(self, intent: Intent) -> IntentVector:
        constraint = self._build_constraint_vector(intent)
        semantic = self._build_semantic_vector(intent)
        combined, method, confidence = self._combine_vectors(constraint, semantic)
        return IntentVector(
            vector=combined,
            projection_method=method,
            constraint_component=constraint,
            semantic_component=semantic,
            confidence=confidence,
        )

    def _alignment_word(self, cosine: float) -> str:
        if cosine >= 0.70:
            return "strongly"
        if cosine >= 0.40:
            return "moderately"
        if cosine >= 0.10:
            return "weakly"
        return "opposingly"

    def _penalty_phrase(self, severity: ContradictionSeverity) -> str:
        if severity == ContradictionSeverity.HARD:
            return "HARD contradiction penalised -0.40"
        if severity == ContradictionSeverity.SOFT:
            return "SOFT contradiction penalised -0.18"
        return "no contradiction penalty"

    def _compute_resonance(self, sigil: Sigil, intent_vector: IntentVector) -> ResonanceScore:
        cosine = sigil.semantic_vector.cosine_similarity(intent_vector.vector)
        raw_norm = (cosine + 1.0) / 2.0
        if sigil.contradiction_severity == ContradictionSeverity.HARD:
            penalty = 0.40
        elif sigil.contradiction_severity == ContradictionSeverity.SOFT:
            penalty = 0.18
        else:
            penalty = 0.0
        penalized = max(0.0, raw_norm - penalty)
        ceiling = float(sigil.resonance_ceiling)
        adjusted = min(penalized, ceiling)
        ceiling_applied = adjusted < penalized - 1e-12
        align = self._alignment_word(cosine)
        pen = self._penalty_phrase(sigil.contradiction_severity)
        ceil_desc = (
            f"applied at {ceiling:.2f}" if ceiling_applied else "not reached"
        )
        proof = (
            f"Intent vector aligns {align} with {sigil.name} (cosine {cosine:.3f}); "
            f"{pen}; ceiling {ceil_desc}."
        )
        return ResonanceScore(
            raw=raw_norm,
            adjusted=adjusted,
            ceiling_applied=ceiling_applied,
            proof=proof,
        )

    def _verdict_type(self, adjusted: float) -> VerdictType:
        if adjusted >= 0.75:
            return VerdictType.COHERENT
        if adjusted >= 0.45:
            return VerdictType.PARTIAL
        return VerdictType.INCOHERENT

    def _casting_note(
        self, sigil: Sigil, verdict_type: VerdictType, intent_vector: IntentVector
    ) -> str:
        _ = intent_vector
        return _CASTING_NOTES.get(
            (verdict_type, sigil.effect_class),
            _CASTING_NOTE_FALLBACK[verdict_type],
        )

    def _effect_description(self, sigil: Sigil, verdict_type: VerdictType) -> str:
        return f"Evaluation for {sigil.name} ({verdict_type.name})."

    def _incoherence_reason(
        self,
        sigil: Sigil,
        verdict_type: VerdictType,
        cosine: float,
    ) -> Optional[str]:
        if verdict_type == VerdictType.COHERENT:
            return None
        key = _canonical_aspect_key(sigil.aspects)
        contra = self._load_contradictions().get(key)
        if (
            sigil.contradiction_severity != ContradictionSeverity.NONE
            and contra is not None
        ):
            reason = contra.get("reason")
            if isinstance(reason, str) and reason.strip():
                return reason
        return (
            f"Geometric misalignment between intent projection and sigil semantic vector "
            f"(cosine {cosine:.3f})."
        )

    def evaluate(self, sigil: Sigil, intent: Intent) -> Verdict:
        try:
            intent_vector = self._build_intent_vector(intent)
            resonance = self._compute_resonance(sigil, intent_vector)
            vt = self._verdict_type(resonance.adjusted)
            cosine = sigil.semantic_vector.cosine_similarity(intent_vector.vector)
            casting = self._casting_note(sigil, vt, intent_vector)
            incoh = self._incoherence_reason(sigil, vt, cosine)
            effect_desc = self._effect_description(sigil, vt)
            return Verdict(
                verdict_type=vt,
                resonance=resonance,
                effect_description=effect_desc,
                incoherence_reason=incoh,
                casting_note=casting,
                intent_vector=intent_vector,
            )
        except Exception:
            z = SemanticVector(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
            iv = IntentVector(
                vector=z,
                projection_method=ProjectionMethod.PARTIAL,
                constraint_component=z,
                semantic_component=None,
                confidence=0.60,
            )
            rs = ResonanceScore(
                raw=0.0,
                adjusted=0.0,
                ceiling_applied=False,
                proof="Intent vector aligns opposingly with sigil (cosine 0.000); no contradiction penalty; ceiling not reached.",
            )
            return Verdict(
                verdict_type=VerdictType.INCOHERENT,
                resonance=rs,
                effect_description="Evaluation failed; incoherent fallback.",
                incoherence_reason="Evaluation raised an unexpected error; incoherent fallback applied.",
                casting_note=_CASTING_NOTE_FALLBACK[VerdictType.INCOHERENT],
                intent_vector=iv,
            )

    def cast(self, aspects: frozenset[AspectID], intent: Intent) -> CastResult:
        sigil = self.composition_engine.compose(aspects)
        verdict = self.evaluate(sigil, intent)
        return CastResult(intent=intent, sigil=sigil, verdict=verdict)

    def accumulate(
        self, result: CastResult, seeds: list[GlyphSeed]
    ) -> Optional[GlyphSeed]:
        aspects = result.sigil.aspects
        matching: Optional[GlyphSeed] = None
        for s in seeds:
            if s.aspect_pattern == aspects:
                matching = s
                break
        vt = result.verdict.verdict_type
        if vt == VerdictType.INCOHERENT and matching is None:
            return None
        adj = float(result.verdict.resonance.adjusted)
        coh_increment = 1.0 if vt == VerdictType.COHERENT else 0.0

        if matching is not None:
            n = matching.observed_count + 1
            new_mean = (
                matching.mean_resonance * matching.observed_count + adj
            ) / n
            new_coh = (
                matching.coherence_rate * matching.observed_count + coh_increment
            ) / n
            cand = (
                result.sigil.effect_class
                if matching.candidate_effect_class is None
                else matching.candidate_effect_class
            )
            return GlyphSeed(
                aspect_pattern=matching.aspect_pattern,
                observed_count=n,
                mean_resonance=new_mean,
                coherence_rate=new_coh,
                candidate_effect_class=cand,
                crystallized=False,
            )

        return GlyphSeed(
            aspect_pattern=aspects,
            observed_count=1,
            mean_resonance=adj,
            coherence_rate=coh_increment,
            candidate_effect_class=result.sigil.effect_class,
            crystallized=False,
        )

    def crystallize(self, seed: GlyphSeed) -> Optional[Sigil]:
        if (
            seed.observed_count < 10
            or seed.mean_resonance < 0.70
            or seed.coherence_rate < 0.65
            or seed.crystallized
        ):
            return None
        if seed.candidate_effect_class is None:
            return None
        base = self.composition_engine.compose(seed.aspect_pattern)
        name = f"Glyph:{base.name}"
        ceiling = round(float(seed.mean_resonance), 2)
        return Sigil(
            name=name,
            aspects=seed.aspect_pattern,
            effect_class=seed.candidate_effect_class,
            resonance_ceiling=ceiling,
            contradiction_severity=base.contradiction_severity,
        )
