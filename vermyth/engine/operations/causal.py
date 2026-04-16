from __future__ import annotations

from vermyth.schema import (
    CastProvenance,
    CastResult,
    CausalEdge,
    CausalEdgeType,
    CausalSubgraph,
    Intent,
    VerdictType,
)


def infer_causal_edge(engine, source: CastResult, target: CastResult) -> CausalEdge | None:
    if source.timestamp >= target.timestamp:
        return None
    sim = source.sigil.semantic_vector.cosine_similarity(target.sigil.semantic_vector)
    dt = (target.timestamp - source.timestamp).total_seconds()
    time_weight = 1.0 / (1.0 + max(0.0, dt) / 3600.0)
    strength = max(0.0, min(1.0, ((sim + 1.0) / 2.0) * time_weight))
    if strength < 0.20:
        return None

    if sim >= 0.55:
        edge_type = CausalEdgeType.CAUSES
    elif sim <= -0.25:
        edge_type = CausalEdgeType.INHIBITS
    elif (
        source.verdict.verdict_type == VerdictType.COHERENT
        and target.verdict.verdict_type == VerdictType.COHERENT
    ):
        edge_type = CausalEdgeType.ENABLES
    else:
        edge_type = CausalEdgeType.REQUIRES

    return CausalEdge(
        source_cast_id=source.cast_id,
        target_cast_id=target.cast_id,
        edge_type=edge_type,
        weight=strength,
        evidence=f"sim={sim:.3f}, dt_seconds={dt:.1f}",
    )


def evaluate_narrative(engine, edges: list[CausalEdge]) -> float:
    if not edges:
        return 0.0
    pair_types: dict[tuple[str, str], set[CausalEdgeType]] = {}
    weight_sum = 0.0
    for edge in edges:
        key = (edge.source_cast_id, edge.target_cast_id)
        pair_types.setdefault(key, set()).add(edge.edge_type)
        weight_sum += float(edge.weight)

    contradictions = 0
    for types in pair_types.values():
        if CausalEdgeType.CAUSES in types and CausalEdgeType.INHIBITS in types:
            contradictions += 1
    contradiction_penalty = min(1.0, contradictions / max(1, len(pair_types)))
    avg_weight = weight_sum / float(len(edges))
    score = avg_weight * (1.0 - 0.5 * contradiction_penalty)
    return max(0.0, min(1.0, score))


def predictive_cast(engine, graph: CausalSubgraph, intent: Intent) -> CastResult:
    seed = engine._build_intent_vector(intent).vector
    alpha = 0.1 + 0.4 * float(graph.narrative_coherence)
    target = engine.composition_engine.interpolate(seed).semantic_vector
    blended = engine._blend_toward(seed, target, alpha)
    result, _ = engine.auto_cast(
        blended,
        intent,
        max_depth=4,
        target_resonance=max(0.65, float(graph.narrative_coherence)),
        blend_alpha=0.35,
    )
    base_provenance = result.provenance or CastProvenance(source="fluid")
    return CastResult.model_construct(
        cast_id=result.cast_id,
        timestamp=result.timestamp,
        intent=result.intent,
        sigil=result.sigil,
        verdict=result.verdict,
        immutable=True,
        lineage=result.lineage,
        glyph_seed_id=result.glyph_seed_id,
        provenance=CastProvenance(
            source=base_provenance.source,
            crystallized_sigil_name=base_provenance.crystallized_sigil_name,
            generation=base_provenance.generation,
            narrative_coherence=float(graph.narrative_coherence),
            causal_root_cast_id=str(graph.root_cast_id),
        ),
    )
