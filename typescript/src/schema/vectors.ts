import { createHash } from "node:crypto";

import type { Aspect } from "./aspect.js";
import { aspectName, aspectPolarity, aspectEntropy } from "./aspect.js";
import { fullAspectOrder, getBasisVersion } from "../registry.js";

export interface SemanticVector {
  readonly components: readonly number[];
  readonly basisVersion: number | null;
}

export function createSemanticVector(
  components: readonly number[],
  basisVersion: number | null = null,
): SemanticVector {
  if (components.length < 6) {
    throw new Error("components must contain at least six floats");
  }
  return {
    components: components.map((x) => Number(x)),
    basisVersion,
  };
}

export function normalizedBasisVersion(vec: SemanticVector): number {
  if (vec.basisVersion === null || vec.basisVersion === undefined) {
    return 0;
  }
  return Math.floor(vec.basisVersion);
}

export function semanticVectorFromAspects(aspects: ReadonlySet<Aspect>): SemanticVector {
  const order = fullAspectOrder();
  const names = new Set([...aspects].map((a) => aspectName(a)));
  const out: number[] = [];
  for (const aspect of order) {
    if (names.has(aspect.name)) {
      const sign = aspectPolarity(aspect) === 1 ? 1 : -1;
      out.push(aspectEntropy(aspect) * sign);
    } else {
      out.push(0);
    }
  }
  return createSemanticVector(out, getBasisVersion());
}

export function upsampleSemanticVector(
  vec: SemanticVector,
  targetVersion: number,
  targetDim?: number,
): SemanticVector {
  const targetV = Math.max(0, Math.floor(targetVersion));
  let comps = [...vec.components];
  if (targetDim !== undefined && targetDim > comps.length) {
    comps = comps.concat(Array(targetDim - comps.length).fill(0));
  }
  return createSemanticVector(comps, targetV);
}

function l2Norm(vec: SemanticVector): number {
  let s = 0;
  for (const c of vec.components) {
    s += c * c;
  }
  const n = Math.sqrt(s);
  if (!Number.isFinite(n)) {
    return 0;
  }
  return n;
}

export function cosineSimilarity(a: SemanticVector, b: SemanticVector): number {
  const aBasis = normalizedBasisVersion(a);
  const bBasis = normalizedBasisVersion(b);
  if (aBasis !== bBasis) {
    throw new Error(
      `incompatible basis versions: left=v${String(aBasis)} right=v${String(bBasis)}; upsample explicitly first`,
    );
  }
  const na = l2Norm(a);
  const nb = l2Norm(b);
  if (na === 0 || nb === 0) {
    return 0;
  }
  const dim = Math.max(a.components.length, b.components.length);
  let dot = 0;
  for (let i = 0; i < dim; i++) {
    const av = i < a.components.length ? a.components[i]! : 0;
    const bv = i < b.components.length ? b.components[i]! : 0;
    dot += av * bv;
  }
  const denom = na * nb;
  if (denom === 0 || !Number.isFinite(dot) || !Number.isFinite(denom)) {
    return 0;
  }
  const sim = dot / denom;
  if (!Number.isFinite(sim)) {
    return 0;
  }
  if (sim > 1) {
    return 1;
  }
  if (sim < -1) {
    return -1;
  }
  return sim;
}

export function vectorDistance(a: SemanticVector, b: SemanticVector): number {
  return 1 - cosineSimilarity(a, b);
}

export function semanticFingerprintForAspects(aspects: ReadonlySet<Aspect>): string {
  const joined = [...aspects].map((x) => aspectName(x)).sort().join("+");
  return createHash("sha256").update(joined, "utf8").digest("hex");
}
