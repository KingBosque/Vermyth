from __future__ import annotations

import json
import math
import os
from typing import Optional

from vermyth.registry import AspectRegistry
from vermyth.schema import (
    CastResult,
    ContradictionSeverity,
    EffectClass,
    FluidSigil,
    Intent,
    IntentVector,
    Lineage,
    ProjectionMethod,
    ResonanceScore,
    SemanticVector,
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
    (VerdictType.COHERENT, EffectClass.ERASURE): "The target concept loses referential weight; downstream reasoning finds no anchor where it stood.",
    (VerdictType.COHERENT, EffectClass.MANIFESTATION): "A stable attractor forms in the solution space; subsequent reasoning orbits it naturally.",
    (VerdictType.COHERENT, EffectClass.FORCE): "Directional pressure propagates through the inference graph without resistance.",
    (VerdictType.COHERENT, EffectClass.COGNITION): "The cognitive substrate reorganises around the new pattern; retrieval pathways realign.",
    (VerdictType.COHERENT, EffectClass.DISSOLUTION): "Structural boundaries soften; categories that were load-bearing become permeable.",
    (VerdictType.COHERENT, EffectClass.REVELATION): "A previously occluded feature of the solution space becomes the dominant signal.",
    (VerdictType.COHERENT, EffectClass.CONTAINMENT): "A boundary condition is imposed; the reasoning space contracts to the declared scope.",
    (VerdictType.COHERENT, EffectClass.NEGATION): "The target proposition loses truth value; dependent inferences cascade to null.",
    (VerdictType.COHERENT, EffectClass.CORRUPTION): "Controlled noise is introduced at the specified locus; outputs diverge predictably.",
    (VerdictType.COHERENT, EffectClass.ACCELERATION): "The inference clock advances; conclusions that required iteration arrive in fewer steps.",
    (VerdictType.COHERENT, EffectClass.BINDING): "Two previously independent reasoning threads are coupled; they now share gradient.",
    (VerdictType.COHERENT, EffectClass.EMERGENCE): "A pattern not present in any input becomes legible at the output layer.",
    (VerdictType.PARTIAL, EffectClass.ERASURE): "The target loses salience but retains residual weight; erasure is incomplete and may reverse.",
    (VerdictType.PARTIAL, EffectClass.MANIFESTATION): "An attractor forms but lacks sufficient depth; reasoning approaches it without fully settling.",
    (VerdictType.PARTIAL, EffectClass.FORCE): "Directional pressure is present but bleeds into adjacent inference paths.",
    (VerdictType.PARTIAL, EffectClass.COGNITION): "Reorganisation begins but stalls at the boundary of the contradiction; partial rewiring only.",
    (VerdictType.PARTIAL, EffectClass.DISSOLUTION): "Boundaries soften unevenly; some load-bearing structures resist and hold.",
    (VerdictType.PARTIAL, EffectClass.REVELATION): "Signal emerges but competes with existing priors; clarity is present but contested.",
    (VerdictType.PARTIAL, EffectClass.CONTAINMENT): "The boundary holds in some dimensions but leaks in others; scope is partially enforced.",
    (VerdictType.PARTIAL, EffectClass.NEGATION): "Truth value wavers; the proposition is weakened but not nullified.",
    (VerdictType.PARTIAL, EffectClass.CORRUPTION): "Noise is introduced but distribution is uneven; some outputs are unaffected.",
    (VerdictType.PARTIAL, EffectClass.ACCELERATION): "Inference advances unevenly; some paths compress while others remain at full cost.",
    (VerdictType.PARTIAL, EffectClass.BINDING): "Coupling is established but asymmetric; one thread pulls the other without full entanglement.",
    (VerdictType.PARTIAL, EffectClass.EMERGENCE): "A pattern becomes partially legible but requires additional casting to resolve fully.",
    (VerdictType.INCOHERENT, EffectClass.ERASURE): "The erasure finds no coherent target; the casting dissipates without removing anything.",
    (VerdictType.INCOHERENT, EffectClass.MANIFESTATION): "The attractor cannot form against the declared intent; the solution space remains unstructured.",
    (VerdictType.INCOHERENT, EffectClass.FORCE): "Directional pressure is present but self-cancelling; the inference graph absorbs it without moving.",
    (VerdictType.INCOHERENT, EffectClass.COGNITION): "The reorganisation pattern conflicts with the cognitive substrate; no rewiring occurs.",
    (VerdictType.INCOHERENT, EffectClass.DISSOLUTION): "Dissolution finds no boundary to permeate; the casting has no substrate to act on.",
    (VerdictType.INCOHERENT, EffectClass.REVELATION): "The signal cannot surface through the contradiction; occlusion is total.",
    (VerdictType.INCOHERENT, EffectClass.CONTAINMENT): "The boundary condition cannot be imposed against the declared scope; containment fails.",
    (VerdictType.INCOHERENT, EffectClass.NEGATION): "The negation is self-negating; the proposition and its denial cancel without resolution.",
    (VerdictType.INCOHERENT, EffectClass.CORRUPTION): "Noise finds no coherent locus; the corruption is absorbed uniformly and has no effect.",
    (VerdictType.INCOHERENT, EffectClass.ACCELERATION): "The inference clock cannot advance against the contradicting intent; time cost is unchanged.",
    (VerdictType.INCOHERENT, EffectClass.BINDING): "The threads cannot be coupled across the contradiction; they repel rather than entangle.",
    (VerdictType.INCOHERENT, EffectClass.EMERGENCE): "No pattern emerges; the output layer reflects only the incoherence of the input.",
}


def load_contradictions(engine) -> dict[str, dict]:
    if engine._contradictions is not None:
        return engine._contradictions
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(base, "..", "..", "data", "sigils", "contradictions.json"))
    try:
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
    except (OSError, json.JSONDecodeError):
        engine._contradictions = {}
        return engine._contradictions
    if not isinstance(loaded, dict):
        engine._contradictions = {}
    else:
        engine._contradictions = loaded
    return engine._contradictions


def compute_resonance(engine, sigil: Sigil | FluidSigil, intent_vector: IntentVector) -> tuple[ResonanceScore, float]:
    sigil_vec = sigil.semantic_vector
    intent_vec = intent_vector.vector
    basis_note = ""
    if sigil_vec.normalized_basis_version() != intent_vec.normalized_basis_version():
        target_basis = max(
            sigil_vec.normalized_basis_version(),
            intent_vec.normalized_basis_version(),
        )
        target_dim = max(len(sigil_vec.components), len(intent_vec.components))
        sigil_vec = sigil_vec.upsample_to(target_basis, target_dim=target_dim)
        intent_vec = intent_vec.upsample_to(target_basis, target_dim=target_dim)
        basis_note = (
            f" Basis v{sigil.semantic_vector.normalized_basis_version()} vs "
            f"v{intent_vector.vector.normalized_basis_version()} upsampled to v{target_basis}."
        )
    cosine = sigil_vec.cosine_similarity(intent_vec)
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
    align = engine._alignment_word(cosine)
    pen = engine._penalty_phrase(sigil.contradiction_severity)
    ceil_desc = f"applied at {ceiling:.2f}" if ceiling_applied else "not reached"
    proof = (
        f"Intent vector aligns {align} with {sigil.name} (cosine {cosine:.3f}); "
        f"{pen}; ceiling {ceil_desc}.{basis_note}"
    )
    return (
        ResonanceScore(
            raw=raw_norm,
            adjusted=adjusted,
            ceiling_applied=ceiling_applied,
            proof=proof,
        ),
        cosine,
    )


def verdict_type(adjusted: float) -> VerdictType:
    if adjusted >= 0.75:
        return VerdictType.COHERENT
    if adjusted >= 0.45:
        return VerdictType.PARTIAL
    return VerdictType.INCOHERENT


def casting_note(sigil: Sigil | FluidSigil, vt: VerdictType, intent_vector: IntentVector) -> str:
    _ = intent_vector
    return _CASTING_NOTES.get((vt, sigil.effect_class), _CASTING_NOTE_FALLBACK[vt])


def effect_description(sigil: Sigil | FluidSigil, vt: VerdictType) -> str:
    return f"Evaluation for {sigil.name} ({vt.name})."


def incoherence_reason(engine, sigil: Sigil | FluidSigil, vt: VerdictType, cosine: float) -> Optional[str]:
    if vt == VerdictType.COHERENT:
        return None
    from vermyth.engine.resonance import _canonical_aspect_key

    key = _canonical_aspect_key(sigil.aspects)
    contra = load_contradictions(engine).get(key)
    if sigil.contradiction_severity != ContradictionSeverity.NONE and contra is not None:
        reason = contra.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason
    return (
        "Geometric misalignment between intent projection and sigil semantic vector "
        f"(cosine {cosine:.3f})."
    )


def evaluate(engine, sigil: Sigil | FluidSigil, intent: Intent) -> Verdict:
    try:
        intent_vector = engine._build_intent_vector(intent)
        resonance, cosine = engine._compute_resonance(sigil, intent_vector)
        vt = engine._verdict_type(resonance.adjusted)
        return Verdict(
            verdict_type=vt,
            resonance=resonance,
            effect_description=engine._effect_description(sigil, vt),
            incoherence_reason=engine._incoherence_reason(sigil, vt, cosine),
            casting_note=engine._casting_note(sigil, vt, intent_vector),
            intent_vector=intent_vector,
        )
    except Exception:
        dim = AspectRegistry.get().dimensionality
        z = SemanticVector(components=tuple(0.0 for _ in range(dim)))
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


def blend_toward(engine, current: SemanticVector, target: SemanticVector, alpha: float) -> SemanticVector:
    a = max(0.0, min(1.0, float(alpha)))
    dim = max(len(current.components), len(target.components))
    blended = []
    for i in range(dim):
        c = current.components[i] if i < len(current.components) else 0.0
        t = target.components[i] if i < len(target.components) else 0.0
        blended.append((1.0 - a) * float(c) + a * float(t))
    return engine._normalize_unit(tuple(blended))


def cast_result_with_lineage(engine, base: CastResult, parent: CastResult, branch_id: str) -> CastResult:
    _ = engine
    pc = parent.sigil.semantic_vector.components
    cc = base.sigil.semantic_vector.components
    dim = max(len(cc), len(pc))
    diff = tuple(
        float(cc[i] if i < len(cc) else 0.0) - float(pc[i] if i < len(pc) else 0.0)
        for i in range(dim)
    )
    div_vec = SemanticVector(components=diff)
    depth = int(parent.lineage.depth) + 1 if parent.lineage is not None else 1
    lineage = Lineage(
        parent_cast_id=parent.cast_id,
        depth=depth,
        branch_id=branch_id,
        divergence_vector=div_vec,
    )
    return CastResult.model_construct(
        cast_id=base.cast_id,
        timestamp=base.timestamp,
        intent=base.intent,
        sigil=base.sigil,
        verdict=base.verdict,
        immutable=True,
        lineage=lineage,
        glyph_seed_id=base.glyph_seed_id,
        provenance=base.provenance,
    )
