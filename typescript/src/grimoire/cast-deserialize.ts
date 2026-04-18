import { AspectRegistry } from "../registry.js";
import { buildSigil } from "../schema/sigil.js";
import type { CastResult } from "../schema/cast-result.js";
import type { Intent } from "../schema/intent.js";
import type { ResonanceScore, Verdict } from "../schema/verdict.js";
import type { IntentVector } from "../schema/intent.js";
import { createSemanticVector } from "../schema/vectors.js";
import type { ContradictionSeverity, EffectClass, VerdictType } from "../schema/enums.js";
import type { ProjectionMethod } from "../schema/enums.js";

type Row = Record<string, unknown>;

function parseIntentJson(raw: unknown): Intent {
  const o = raw as Record<string, unknown>;
  return {
    objective: String(o["objective"] ?? ""),
    scope: String(o["scope"] ?? ""),
    reversibility: o["reversibility"] as Intent["reversibility"],
    sideEffectTolerance: (o["side_effect_tolerance"] ?? o["sideEffectTolerance"]) as Intent["sideEffectTolerance"],
  };
}

export function deserializeCastResult(row: Row): CastResult {
  const intent = parseIntentJson(JSON.parse(String(row["intent_json"])));
  const sigilD = JSON.parse(String(row["sigil_json"])) as {
    name: string;
    aspects: string[];
    effect_class: string;
    resonance_ceiling: number;
    contradiction_severity: string;
    semantic_fingerprint: string;
    semantic_vector: number[];
    polarity: string;
    basis_version?: number;
  };
  const registry = AspectRegistry.get();
  const dim = registry.dimensionality;
  const pad = (comps: number[]) => {
    const c = [...comps];
    while (c.length < dim) {
      c.push(0);
    }
    return c;
  };
  const aspects = new Set(sigilD.aspects.map((n) => registry.resolve(n)));
  const baseSigil = buildSigil({
    name: sigilD.name,
    aspects,
    effectClass: sigilD.effect_class as EffectClass,
    resonanceCeiling: sigilD.resonance_ceiling,
    contradictionSeverity: sigilD.contradiction_severity as ContradictionSeverity,
  });
  const storedVec = Array.isArray(sigilD.semantic_vector)
    ? (sigilD.semantic_vector as number[]).map(Number)
    : [];
  const semanticVector =
    storedVec.length > 0
      ? createSemanticVector(pad(storedVec), sigilD.basis_version ?? null)
      : baseSigil.semanticVector;
  const sigil = {
    ...baseSigil,
    semanticFingerprint: String(sigilD.semantic_fingerprint ?? baseSigil.semanticFingerprint),
    semanticVector,
  };

  const vj = JSON.parse(String(row["verdict_json"])) as {
    verdict_type: string;
    resonance: Record<string, unknown>;
    effect_description: string;
    incoherence_reason: string | null;
    casting_note: string;
    intent_vector: {
      vector: { components: number[]; basis_version?: number };
      projection_method: string;
      constraint_component: { components: number[]; basis_version?: number };
      semantic_component: { components: number[]; basis_version?: number } | null;
      confidence: number;
    };
  };

  const ivRaw = vj.intent_vector;
  const vecComps = pad(ivRaw.vector.components ?? []);
  const ccComps = pad(ivRaw.constraint_component.components ?? []);
  const sc =
    ivRaw.semantic_component === null
      ? null
      : createSemanticVector(
          pad(ivRaw.semantic_component.components ?? []),
          ivRaw.semantic_component.basis_version ?? null,
        );

  const intentVector: IntentVector = {
    vector: createSemanticVector(vecComps, ivRaw.vector.basis_version ?? null),
    projectionMethod: ivRaw.projection_method as ProjectionMethod,
    constraintComponent: createSemanticVector(ccComps, ivRaw.constraint_component.basis_version ?? null),
    semanticComponent: sc,
    confidence: ivRaw.confidence,
  };

  const resRaw = vj.resonance;
  const resonance: ResonanceScore = {
    raw: Number(resRaw["raw"]),
    adjusted: Number(resRaw["adjusted"]),
    ceilingApplied: Boolean(resRaw["ceiling_applied"] ?? resRaw["ceilingApplied"]),
    proof: String(resRaw["proof"] ?? ""),
  };

  const verdict: Verdict = {
    verdictType: vj.verdict_type as VerdictType,
    resonance,
    effectDescription: vj.effect_description,
    incoherenceReason: vj.incoherence_reason,
    castingNote: vj.casting_note,
    intentVector,
  };

  const lineageJson = row["lineage_json"];
  const lineage =
    lineageJson === null || lineageJson === undefined
      ? null
      : JSON.parse(String(lineageJson));

  const provenanceJson = row["provenance_json"];
  const provenance =
    provenanceJson === null || provenanceJson === undefined
      ? null
      : JSON.parse(String(provenanceJson));

  return {
    castId: String(row["cast_id"]),
    timestamp: new Date(String(row["timestamp"])),
    intent,
    sigil,
    verdict,
    immutable: true,
    lineage: lineage as CastResult["lineage"],
    glyphSeedId: row["glyph_seed_id"] === null ? null : String(row["glyph_seed_id"]),
    provenance: provenance as CastResult["provenance"],
  };
}
