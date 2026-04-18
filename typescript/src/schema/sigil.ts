import type { ContradictionSeverity, EffectClass, Polarity } from "./enums.js";
import { Polarity as Pol } from "./enums.js";
import type { Aspect } from "./aspect.js";
import { aspectPolarity } from "./aspect.js";
import type { SemanticVector } from "./vectors.js";
import {
  cosineSimilarity,
  createSemanticVector,
  semanticFingerprintForAspects,
  semanticVectorFromAspects,
} from "./vectors.js";

export interface Sigil {
  readonly name: string;
  readonly aspects: ReadonlySet<Aspect>;
  readonly effectClass: EffectClass;
  readonly resonanceCeiling: number;
  readonly contradictionSeverity: ContradictionSeverity;
  readonly semanticFingerprint: string;
  readonly semanticVector: SemanticVector;
  readonly polarity: Polarity;
}

export interface FluidSigil extends Sigil {
  readonly sourceVector: SemanticVector;
  readonly nearestCanonical: string;
  readonly interpolationWeights: Readonly<Record<string, number>>;
}

function polarityFromAspects(aspects: ReadonlySet<Aspect>): Polarity {
  let net = 0;
  for (const a of aspects) {
    net += aspectPolarity(a);
  }
  if (net > 0) {
    return Pol.POSITIVE;
  }
  if (net < 0) {
    return Pol.NEGATIVE;
  }
  return Pol.NEUTRAL;
}

export function buildSigil(params: {
  name: string;
  aspects: ReadonlySet<Aspect>;
  effectClass: EffectClass;
  resonanceCeiling: number;
  contradictionSeverity: ContradictionSeverity;
}): Sigil {
  const semanticVector = semanticVectorFromAspects(params.aspects);
  return {
    name: params.name,
    aspects: params.aspects,
    effectClass: params.effectClass,
    resonanceCeiling: params.resonanceCeiling,
    contradictionSeverity: params.contradictionSeverity,
    semanticFingerprint: semanticFingerprintForAspects(params.aspects),
    semanticVector,
    polarity: polarityFromAspects(params.aspects),
  };
}

export function buildFluidSigil(params: {
  name: string;
  aspects: ReadonlySet<Aspect>;
  effectClass: EffectClass;
  resonanceCeiling: number;
  contradictionSeverity: ContradictionSeverity;
  semanticVector: SemanticVector;
  polarity: Polarity;
  semanticFingerprint: string;
  sourceVector: SemanticVector;
  nearestCanonical: string;
  interpolationWeights: Readonly<Record<string, number>>;
}): FluidSigil {
  return {
    name: params.name,
    aspects: params.aspects,
    effectClass: params.effectClass,
    resonanceCeiling: params.resonanceCeiling,
    contradictionSeverity: params.contradictionSeverity,
    semanticFingerprint: params.semanticFingerprint,
    semanticVector: params.semanticVector,
    polarity: params.polarity,
    sourceVector: params.sourceVector,
    nearestCanonical: params.nearestCanonical,
    interpolationWeights: params.interpolationWeights,
  };
}

/** Normalize user vector to unit length (matches CompositionEngine._normalize_unit). */
export function normalizeSemanticVectorForComposition(vec: SemanticVector): SemanticVector {
  let s = 0;
  for (const c of vec.components) {
    s += c * c;
  }
  const n = Math.sqrt(s);
  if (n === 0 || !Number.isFinite(n)) {
    return createSemanticVector(
      vec.components.map(() => 0),
      vec.basisVersion ?? null,
    );
  }
  return createSemanticVector(
    vec.components.map((c) => c / n),
    vec.basisVersion ?? null,
  );
}

export function fluidPolarityFromVector(vec: SemanticVector): Polarity {
  let net = 0;
  for (const c of vec.components) {
    if (c > 1e-12) {
      net += 1;
    } else if (c < -1e-12) {
      net -= 1;
    }
  }
  if (net > 0) {
    return Pol.POSITIVE;
  }
  if (net < 0) {
    return Pol.NEGATIVE;
  }
  return Pol.NEUTRAL;
}

export function cosineSigilIntent(sigilVec: SemanticVector, intentVec: SemanticVector): number {
  return cosineSimilarity(sigilVec, intentVec);
}
