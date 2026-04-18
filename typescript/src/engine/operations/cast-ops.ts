import { readFileSync } from "node:fs";
import { join } from "node:path";

import { sigilsDir } from "../../paths.js";
import { AspectRegistry } from "../../registry.js";
import { canonicalAspectKey } from "../keys.js";
import type { ContradictionSeverity } from "../../schema/enums.js";
import { ContradictionSeverity as CS } from "../../schema/enums.js";
import { VerdictType as VT } from "../../schema/enums.js";
import type { Intent } from "../../schema/intent.js";
import type { IntentVector } from "../../schema/intent.js";
import { fallbackIntentVector } from "../../schema/intent.js";
import type { FluidSigil, Sigil } from "../../schema/sigil.js";
import type { Verdict, ResonanceScore } from "../../schema/verdict.js";
import type { SemanticVector } from "../../schema/vectors.js";
import {
  cosineSimilarity,
  normalizedBasisVersion,
  upsampleSemanticVector,
} from "../../schema/vectors.js";
import * as intentOps from "./intent-ops.js";
import { CASTING_NOTE_FALLBACK, CASTING_NOTES, type CastingNoteKey } from "./cast-notes.js";

export interface CastEngineLike {
  contradictions: Record<string, Record<string, unknown>> | null;
  computeResonance(
    sigil: Sigil | FluidSigil,
    intentVector: IntentVector,
  ): { score: ResonanceScore; cosine: number };
  verdictType(adjusted: number): import("../../schema/enums.js").VerdictType;
  castingNote(sigil: Sigil | FluidSigil, vt: import("../../schema/enums.js").VerdictType, iv: IntentVector): string;
  effectDescription(sigil: Sigil | FluidSigil, vt: import("../../schema/enums.js").VerdictType): string;
  incoherenceReason(
    sigil: Sigil | FluidSigil,
    vt: import("../../schema/enums.js").VerdictType,
    cosine: number,
  ): string | null;
  buildIntentVector(intent: Intent): IntentVector;
}

export function loadContradictionsFromDisk(
  engine: { contradictions: Record<string, Record<string, unknown>> | null },
): Record<string, Record<string, unknown>> {
  if (engine.contradictions !== null) {
    return engine.contradictions;
  }
  const path = join(sigilsDir(), "contradictions.json");
  try {
    const loaded = JSON.parse(readFileSync(path, "utf8")) as unknown;
    if (loaded && typeof loaded === "object" && !Array.isArray(loaded)) {
      engine.contradictions = loaded as Record<string, Record<string, unknown>>;
    } else {
      engine.contradictions = {};
    }
  } catch {
    engine.contradictions = {};
  }
  return engine.contradictions ?? {};
}

export function computeResonance(
  _engine: CastEngineLike,
  sigil: Sigil | FluidSigil,
  intentVector: IntentVector,
): { score: ResonanceScore; cosine: number } {
  let sigilVec = sigil.semanticVector;
  let intentVec = intentVector.vector;
  let basisNote = "";
  if (normalizedBasisVersion(sigilVec) !== normalizedBasisVersion(intentVec)) {
    const targetBasis = Math.max(
      normalizedBasisVersion(sigilVec),
      normalizedBasisVersion(intentVec),
    );
    const targetDim = Math.max(sigilVec.components.length, intentVec.components.length);
    sigilVec = upsampleSemanticVector(sigilVec, targetBasis, targetDim);
    intentVec = upsampleSemanticVector(intentVec, targetBasis, targetDim);
    basisNote = ` Basis v${String(normalizedBasisVersion(sigil.semanticVector))} vs v${String(normalizedBasisVersion(intentVector.vector))} upsampled to v${String(targetBasis)}.`;
  }
  const cosine = cosineSimilarity(sigilVec, intentVec);
  const rawNorm = (cosine + 1) / 2;
  let penalty = 0;
  if (sigil.contradictionSeverity === CS.HARD) {
    penalty = 0.4;
  } else if (sigil.contradictionSeverity === CS.SOFT) {
    penalty = 0.18;
  }
  const penalized = Math.max(0, rawNorm - penalty);
  const ceiling = sigil.resonanceCeiling;
  const adjusted = Math.min(penalized, ceiling);
  const ceilingApplied = adjusted < penalized - 1e-12;
  const align = intentOps.alignmentWord(cosine);
  const pen = intentOps.penaltyPhrase(sigil.contradictionSeverity as ContradictionSeverity);
  const ceilDesc = ceilingApplied ? `applied at ${ceiling.toFixed(2)}` : "not reached";
  const proof =
    `Intent vector aligns ${align} with ${sigil.name} (cosine ${cosine.toFixed(3)}); ` +
    `${pen}; ceiling ${ceilDesc}.${basisNote}`;
  return {
    score: {
      raw: rawNorm,
      adjusted,
      ceilingApplied,
      proof,
    },
    cosine,
  };
}

export function verdictType(adjusted: number): import("../../schema/enums.js").VerdictType {
  if (adjusted >= 0.75) {
    return VT.COHERENT;
  }
  if (adjusted >= 0.45) {
    return VT.PARTIAL;
  }
  return VT.INCOHERENT;
}

export function castingNote(
  sigil: Sigil | FluidSigil,
  vt: import("../../schema/enums.js").VerdictType,
  _intentVector: IntentVector,
): string {
  const key = `${vt}:${sigil.effectClass}` as CastingNoteKey;
  return CASTING_NOTES[key] ?? CASTING_NOTE_FALLBACK[vt]!;
}

export function effectDescription(
  sigil: Sigil | FluidSigil,
  vt: import("../../schema/enums.js").VerdictType,
): string {
  return `Evaluation for ${sigil.name} (${vt}).`;
}

export function incoherenceReason(
  engine: CastEngineLike,
  sigil: Sigil | FluidSigil,
  vt: import("../../schema/enums.js").VerdictType,
  cosine: number,
): string | null {
  if (vt === VT.COHERENT) {
    return null;
  }
  const key = canonicalAspectKey(sigil.aspects);
  const cmap = loadContradictionsFromDisk(engine);
  const c = cmap[key];
  if (sigil.contradictionSeverity !== CS.NONE && c !== undefined) {
    const reason = c["reason"];
    if (typeof reason === "string" && reason.trim()) {
      return reason;
    }
  }
  return (
    "Geometric misalignment between intent projection and sigil semantic vector " +
    `(cosine ${cosine.toFixed(3)}).`
  );
}

export function evaluate(
  engine: CastEngineLike,
  sigil: Sigil | FluidSigil,
  intent: Intent,
): Verdict {
  try {
    const intentVector = engine.buildIntentVector(intent);
    const { score: resonance, cosine } = engine.computeResonance(sigil, intentVector);
    const vt = verdictType(resonance.adjusted);
    return {
      verdictType: vt,
      resonance,
      effectDescription: effectDescription(sigil, vt),
      incoherenceReason: incoherenceReason(engine, sigil, vt, cosine),
      castingNote: castingNote(sigil, vt, intentVector),
      intentVector,
    };
  } catch {
    const dim = AspectRegistry.get().dimensionality;
    const iv = fallbackIntentVector(dim);
    const rs: ResonanceScore = {
      raw: 0,
      adjusted: 0,
      ceilingApplied: false,
      proof:
        "Intent vector aligns opposingly with sigil (cosine 0.000); no contradiction penalty; ceiling not reached.",
    };
    return {
      verdictType: VT.INCOHERENT,
      resonance: rs,
      effectDescription: "Evaluation failed; incoherent fallback.",
      incoherenceReason: "Evaluation raised an unexpected error; incoherent fallback applied.",
      castingNote: CASTING_NOTE_FALLBACK[VT.INCOHERENT]!,
      intentVector: iv,
    };
  }
}

export function blendToward(
  engine: { normalizeUnit(components: readonly number[]): SemanticVector },
  current: SemanticVector,
  target: SemanticVector,
  alpha: number,
): SemanticVector {
  const a = Math.max(0, Math.min(1, alpha));
  const dim = Math.max(current.components.length, target.components.length);
  const blended: number[] = [];
  for (let i = 0; i < dim; i++) {
    const c = i < current.components.length ? current.components[i]! : 0;
    const t = i < target.components.length ? target.components[i]! : 0;
    blended.push((1 - a) * c + a * t);
  }
  return engine.normalizeUnit(blended);
}
