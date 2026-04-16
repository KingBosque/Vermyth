from __future__ import annotations

from ulid import ULID

from vermyth.schema import (
    AspectID,
    AutoCastDiagnostics,
    CastProvenance,
    CastResult,
    Intent,
    Lineage,
    SemanticVector,
    VerdictType,
)


def cast(engine, aspects: frozenset[AspectID], intent: Intent) -> CastResult:
    sigil = engine.composition_engine.compose(aspects)
    verdict = engine.evaluate(sigil, intent)
    return CastResult(intent=intent, sigil=sigil, verdict=verdict)


def fluid_cast(engine, vector: SemanticVector, intent: Intent) -> CastResult:
    sigil = engine.composition_engine.interpolate(vector)
    verdict = engine.evaluate(sigil, intent)
    provenance = CastProvenance(source="fluid")
    return CastResult(intent=intent, sigil=sigil, verdict=verdict, provenance=provenance)


def auto_cast(
    engine,
    vector: SemanticVector,
    intent: Intent,
    *,
    max_depth: int = 5,
    target_resonance: float = 0.75,
    blend_alpha: float = 0.35,
    with_diagnostics: bool = False,
) -> tuple[CastResult, list[CastResult]] | tuple[CastResult, list[CastResult], AutoCastDiagnostics]:
    branch_id = str(ULID())
    chain: list[CastResult] = []
    diagnostics_steps: list[dict[str, float]] = []
    current = vector
    parent_cast_id: str | None = None

    for _ in range(max_depth):
        base = fluid_cast(engine, current, intent)
        if parent_cast_id is not None:
            parent_result = chain[-1]
            pc = parent_result.sigil.semantic_vector.components
            cc = base.sigil.semantic_vector.components
            dim = max(len(cc), len(pc))
            diff = tuple(
                float(cc[i] if i < len(cc) else 0.0)
                - float(pc[i] if i < len(pc) else 0.0)
                for i in range(dim)
            )
            div_vec = SemanticVector(components=diff)
            depth_lin = 1
            if parent_result.lineage is not None:
                depth_lin = int(parent_result.lineage.depth) + 1
            lin = Lineage(
                parent_cast_id=parent_cast_id,
                depth=depth_lin,
                branch_id=branch_id,
                divergence_vector=div_vec,
            )
            result = CastResult.model_construct(
                cast_id=base.cast_id,
                timestamp=base.timestamp,
                intent=base.intent,
                sigil=base.sigil,
                verdict=base.verdict,
                immutable=True,
                lineage=lin,
                glyph_seed_id=base.glyph_seed_id,
                provenance=CastProvenance(
                    source="fluid",
                    crystallized_sigil_name=None,
                    generation=None,
                ),
            )
        else:
            result = base

        chain.append(result)
        adj = float(result.verdict.resonance.adjusted)
        diagnostics_steps.append(
            {
                "adjusted": adj,
                "raw": float(result.verdict.resonance.raw),
                "blend_alpha": float(blend_alpha),
            }
        )
        if (
            result.verdict.verdict_type == VerdictType.COHERENT
            and adj >= float(target_resonance)
        ):
            if with_diagnostics:
                return (
                    result,
                    chain,
                    AutoCastDiagnostics(
                        steps=diagnostics_steps,
                        converged=True,
                        final_adjusted=adj,
                    ),
                )
            return result, chain

        fluid = engine.composition_engine.interpolate(current)
        current = engine._blend_toward(current, fluid.semantic_vector, blend_alpha)
        parent_cast_id = result.cast_id

    final = chain[-1]
    final_adj = float(final.verdict.resonance.adjusted)
    if with_diagnostics:
        return (
            final,
            chain,
            AutoCastDiagnostics(
                steps=diagnostics_steps,
                converged=False,
                final_adjusted=final_adj,
            ),
        )
    return final, chain

