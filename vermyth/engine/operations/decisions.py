from __future__ import annotations

from vermyth.contracts import GrimoireContract
from vermyth.schema import (
    AspectID,
    CastProvenance,
    CastResult,
    CausalQuery,
    DivergenceReport,
    DivergenceStatus,
    Intent,
    PolicyAction,
    PolicyDecision,
    PolicyThresholds,
    SemanticVector,
    VerdictType,
)


def decide(
    engine,
    intent: Intent,
    *,
    aspects: frozenset[AspectID] | None = None,
    vector: SemanticVector | None = None,
    parent_cast_id: str | None = None,
    causal_root_cast_id: str | None = None,
    thresholds: PolicyThresholds | None = None,
    grimoire: GrimoireContract | None = None,
) -> tuple[PolicyDecision, CastResult]:
    policy_thresholds = thresholds or PolicyThresholds()

    if aspects is not None and vector is not None:
        raise ValueError("pass either aspects or vector, not both")
    if aspects is not None:
        result = engine.cast(aspects, intent)
    elif vector is not None:
        result = engine.fluid_cast(vector, intent)
    else:
        seed = engine._build_intent_vector(intent).vector
        result, _chain = engine.auto_cast(seed, intent)

    divergence_status: DivergenceStatus | None = None
    if parent_cast_id is not None:
        if grimoire is None:
            raise ValueError("grimoire is required when parent_cast_id is provided")
        parent = grimoire.read(str(parent_cast_id))
        thresholds_obj = grimoire.read_divergence_thresholds()
        report = DivergenceReport.classify(
            cast_id=result.cast_id,
            parent_cast_id=str(parent_cast_id),
            parent_vector=parent.sigil.semantic_vector,
            child_vector=result.sigil.semantic_vector,
            thresholds=thresholds_obj,
        )
        divergence_status = report.status

    narrative_coherence: float | None = None
    if causal_root_cast_id is not None:
        if grimoire is None:
            raise ValueError("grimoire is required when causal_root_cast_id is provided")
        graph = grimoire.causal_subgraph(CausalQuery(root_cast_id=str(causal_root_cast_id)))
        narrative_coherence = engine.evaluate_narrative(graph.edges)

    verdict = result.verdict.verdict_type
    adjusted = float(result.verdict.resonance.adjusted)
    action, rationale = engine._policy_model.decide(
        verdict=verdict,
        adjusted_resonance=adjusted,
        divergence_status=divergence_status,
        narrative_coherence=narrative_coherence,
        thresholds=policy_thresholds,
    )
    suggested_intent = intent if action == PolicyAction.RESHAPE else None

    decision = PolicyDecision(
        action=action,
        rationale=rationale,
        cast_id=result.cast_id,
        suggested_intent=suggested_intent,
        parent_cast_id=parent_cast_id,
        divergence_status=divergence_status,
        narrative_coherence=narrative_coherence,
        thresholds=policy_thresholds,
        model_name=getattr(engine._policy_model, "name", "rule_based"),
        model_version=getattr(engine._policy_model, "version", "1"),
    )
    if narrative_coherence is not None or causal_root_cast_id is not None:
        base_provenance = result.provenance or CastProvenance(source="base")
        result = CastResult.model_construct(
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
                narrative_coherence=narrative_coherence,
                causal_root_cast_id=causal_root_cast_id,
            ),
        )
    return decision, result

