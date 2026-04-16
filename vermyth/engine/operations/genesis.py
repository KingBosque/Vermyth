from __future__ import annotations

import math

from vermyth.registry import AspectRegistry
from vermyth.schema import AspectID, CastResult, EmergentAspect, SemanticVector, VerdictType


def propose_genesis(
    engine,
    cast_history: list[CastResult],
    *,
    min_cluster_size: int = 15,
    min_unexplained_variance: float = 0.3,
    min_coherence_rate: float = 0.6,
) -> list[EmergentAspect]:
    coherent = [
        c
        for c in cast_history
        if c.verdict.verdict_type == VerdictType.COHERENT
        and float(c.verdict.resonance.adjusted) >= 0.75
    ]
    if not coherent:
        return []

    dim = AspectRegistry.get().dimensionality
    canonical_dim = len(AspectID)
    clusters: dict[int, list[CastResult]] = {}
    for cast in coherent:
        comps = cast.sigil.semantic_vector.components
        idx = max(range(len(comps)), key=lambda i: abs(float(comps[i])))
        clusters.setdefault(idx, []).append(cast)

    proposals: list[EmergentAspect] = []
    symbols = ["✧", "✶", "✷", "✹", "✺", "✻", "✼", "✽"]
    for dominant_idx, members in clusters.items():
        if len(members) < int(min_cluster_size):
            continue
        centroid = [0.0 for _ in range(dim)]
        mean_res = 0.0
        coh_count = 0
        for cast in members:
            vec = cast.sigil.semantic_vector.components
            for i in range(dim):
                centroid[i] += float(vec[i] if i < len(vec) else 0.0)
            adj = float(cast.verdict.resonance.adjusted)
            mean_res += adj
            if cast.verdict.verdict_type == VerdictType.COHERENT:
                coh_count += 1
        n = float(len(members))
        centroid = [c / n for c in centroid]
        mean_res /= n
        coherence_rate = float(coh_count) / n if n > 0 else 0.0
        if coherence_rate < float(min_coherence_rate):
            continue

        total_abs = sum(abs(float(v)) for v in centroid) or 1.0
        explained = max(abs(float(v)) for v in centroid[:canonical_dim]) / total_abs
        unexplained = 1.0 - explained
        if dominant_idx < canonical_dim and unexplained < float(min_unexplained_variance):
            continue

        dominant_val = float(centroid[dominant_idx] if dominant_idx < len(centroid) else 0.0)
        polarity = 1 if dominant_val >= 0.0 else -1
        spread = 0.0
        for cast in members:
            comps = cast.sigil.semantic_vector.components
            v = float(comps[dominant_idx] if dominant_idx < len(comps) else 0.0)
            d = v - dominant_val
            spread += d * d
        spread = math.sqrt(spread / n) if n > 0 else 0.0
        entropy = max(0.0, min(1.0, abs(spread)))
        name = f"GENESIS_{dominant_idx}_{len(members)}"
        symbol = symbols[dominant_idx % len(symbols)]
        proposals.append(
            EmergentAspect(
                proposed_name=name,
                derived_polarity=polarity,
                derived_entropy=entropy,
                proposed_symbol=symbol,
                centroid_vector=SemanticVector(components=tuple(centroid)),
                support_count=len(members),
                mean_resonance=max(0.0, min(1.0, mean_res)),
                coherence_rate=max(0.0, min(1.0, coherence_rate)),
                evidence_cast_ids=[m.cast_id for m in members[:10]],
            )
        )
    return proposals
