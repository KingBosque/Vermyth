import { canonicalAspectKey } from "../engine/keys.js";
import type { CastResult } from "../schema/cast-result.js";
import type { Intent } from "../schema/intent.js";
import { aspectName } from "../schema/aspect.js";
import { normalizedBasisVersion } from "../schema/vectors.js";

function intentJson(intent: Intent): string {
  return JSON.stringify({
    objective: intent.objective,
    scope: intent.scope,
    reversibility: intent.reversibility,
    side_effect_tolerance: intent.sideEffectTolerance,
  });
}

export function serializeCastResultRow(result: CastResult): Record<string, unknown> {
  const sig = result.sigil;
  const iv = result.verdict.intentVector;
  const sigilJson = JSON.stringify({
    name: sig.name,
    aspects: [...sig.aspects].map((a) => aspectName(a)),
    effect_class: sig.effectClass,
    resonance_ceiling: sig.resonanceCeiling,
    contradiction_severity: sig.contradictionSeverity,
    semantic_fingerprint: sig.semanticFingerprint,
    semantic_vector: [...sig.semanticVector.components],
    basis_version: normalizedBasisVersion(sig.semanticVector),
    polarity: sig.polarity,
  });
  const verdictJson = JSON.stringify({
    verdict_type: result.verdict.verdictType,
    resonance: {
      raw: result.verdict.resonance.raw,
      adjusted: result.verdict.resonance.adjusted,
      ceiling_applied: result.verdict.resonance.ceilingApplied,
      proof: result.verdict.resonance.proof,
    },
    effect_description: result.verdict.effectDescription,
    incoherence_reason: result.verdict.incoherenceReason,
    casting_note: result.verdict.castingNote,
    intent_vector: {
      vector: {
        components: [...iv.vector.components],
        basis_version: normalizedBasisVersion(iv.vector),
      },
      projection_method: iv.projectionMethod,
      constraint_component: {
        components: [...iv.constraintComponent.components],
        basis_version: normalizedBasisVersion(iv.constraintComponent),
      },
      semantic_component:
        iv.semanticComponent === null
          ? null
          : {
              components: [...iv.semanticComponent.components],
              basis_version: normalizedBasisVersion(iv.semanticComponent),
            },
      confidence: iv.confidence,
    },
  });

  return {
    cast_id: result.castId,
    timestamp: result.timestamp.toISOString(),
    intent_json: intentJson(result.intent),
    sigil_json: sigilJson,
    verdict_json: verdictJson,
    lineage_json: result.lineage
      ? JSON.stringify({
          parent_cast_id: result.lineage.parentCastId,
          depth: result.lineage.depth,
          branch_id: result.lineage.branchId,
          divergence_vector:
            result.lineage.divergenceVector === undefined || result.lineage.divergenceVector === null
              ? null
              : {
                  components: [...result.lineage.divergenceVector.components],
                  basis_version: normalizedBasisVersion(result.lineage.divergenceVector),
                },
        })
      : null,
    glyph_seed_id: result.glyphSeedId ?? null,
    semantic_vector_json: JSON.stringify([...sig.semanticVector.components]),
    verdict_type: result.verdict.verdictType,
    effect_class: sig.effectClass,
    adjusted_resonance: result.verdict.resonance.adjusted,
    branch_id: result.lineage?.branchId ?? null,
    provenance_json: result.provenance
      ? JSON.stringify({
          source: result.provenance.source,
          crystallized_sigil_name: result.provenance.crystallizedSigilName ?? null,
          generation: result.provenance.generation ?? null,
          narrative_coherence: result.provenance.narrativeCoherence ?? null,
          causal_root_cast_id: result.provenance.causalRootCastId ?? null,
        })
      : null,
    aspect_pattern_key: canonicalAspectKey(sig.aspects),
    basis_version: normalizedBasisVersion(sig.semanticVector),
    narrative_coherence:
      result.provenance?.narrativeCoherence !== undefined && result.provenance?.narrativeCoherence !== null
        ? result.provenance.narrativeCoherence
        : null,
    causal_root_cast_id: result.provenance?.causalRootCastId ?? null,
  };
}
