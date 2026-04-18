import type { CastResult } from "../schema/cast-result.js";
import { aspectName } from "../schema/aspect.js";
import type { Grimoire } from "../grimoire/store.js";
import { DivergenceStatus as DS } from "../schema/enums.js";

/**
 * MCP/HTTP cast summary aligned with Python `cast_result_to_dict`
 * (`vermyth/mcp/tools/casting/_legacy.py`).
 */
export function castResultToDict(
  result: CastResult,
  context?: { grimoire?: Grimoire | null },
): Record<string, unknown> {
  const warnings: string[] = [];
  let lineageDict: Record<string, unknown> | null = null;
  if (result.lineage !== undefined && result.lineage !== null) {
    lineageDict = {
      parent_cast_id: result.lineage.parentCastId,
      depth: result.lineage.depth,
      branch_id: result.lineage.branchId,
    };
    if (result.lineage.divergenceVector !== undefined && result.lineage.divergenceVector !== null) {
      lineageDict["divergence_vector"] = [...result.lineage.divergenceVector.components].map((c) =>
        Math.round(c * 1e6) / 1e6,
      );
    }
    const report = context?.grimoire?.readDivergenceReport?.(result.castId) ?? null;
    if (report !== null) {
      lineageDict["divergence"] = {
        l2_magnitude: Math.round(report.l2Magnitude * 1e6) / 1e6,
        cosine_distance: Math.round(report.cosineDistance * 1e6) / 1e6,
        status: report.status,
      };
      if (report.status !== DS.STABLE) {
        warnings.push(`${report.status}: parent-child semantic drift exceeded thresholds`);
      }
    }
  }

  const provenanceDict =
    result.provenance === undefined || result.provenance === null
      ? null
      : {
          source: result.provenance.source,
          crystallized_sigil_name: result.provenance.crystallizedSigilName,
          generation: result.provenance.generation,
          narrative_coherence: result.provenance.narrativeCoherence,
          causal_root_cast_id: result.provenance.causalRootCastId,
        };

  const out: Record<string, unknown> = {
    cast_id: result.castId,
    timestamp: result.timestamp.toISOString(),
    verdict: result.verdict.verdictType,
    resonance: Math.round(result.verdict.resonance.adjusted * 1e4) / 1e4,
    effect_class: result.sigil.effectClass,
    sigil_name: result.sigil.name,
    sigil_aspects: [...result.sigil.aspects].map((a) => aspectName(a)).sort(),
    effect_description: result.verdict.effectDescription,
    casting_note: result.verdict.castingNote,
    incoherence_reason: result.verdict.incoherenceReason,
    proof: result.verdict.resonance.proof,
    projection_method: result.verdict.intentVector.projectionMethod,
    intent_confidence: Math.round(result.verdict.intentVector.confidence * 1e4) / 1e4,
    semantic_vector: [...result.sigil.semanticVector.components].map((c) => Math.round(c * 1e6) / 1e6),
    intent_vector: [...result.verdict.intentVector.vector.components].map((c) => Math.round(c * 1e6) / 1e6),
    lineage: lineageDict,
    glyph_seed_id: result.glyphSeedId,
    provenance: provenanceDict,
  };
  if (warnings.length > 0) {
    out["warnings"] = warnings;
  }
  return out;
}
