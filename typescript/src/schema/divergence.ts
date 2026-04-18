import type { DivergenceStatus } from "./enums.js";
import { DivergenceStatus as DS } from "./enums.js";
import type { SemanticVector } from "./vectors.js";
import { normalizedBasisVersion, upsampleSemanticVector, vectorDistance } from "./vectors.js";

export interface DivergenceThresholds {
  l2StableMax: number;
  l2DivergedMin: number;
  cosineStableMax: number;
  cosineDivergedMin: number;
}

export const defaultDivergenceThresholds = (): DivergenceThresholds => ({
  l2StableMax: 0.3,
  l2DivergedMin: 0.7,
  cosineStableMax: 0.2,
  cosineDivergedMin: 0.5,
});

export interface DivergenceReport {
  castId: string;
  parentCastId: string;
  l2Magnitude: number;
  cosineDistance: number;
  status: DivergenceStatus;
  computedAt: Date;
  basisNote: string | null;
}

export function classifyDivergenceReport(params: {
  castId: string;
  parentCastId: string;
  parentVector: SemanticVector;
  childVector: SemanticVector;
  thresholds: DivergenceThresholds;
}): DivergenceReport {
  let parent = params.parentVector;
  let child = params.childVector;
  let basisNote: string | null = null;
  const pb = normalizedBasisVersion(parent);
  const cb = normalizedBasisVersion(child);
  if (pb !== cb) {
    const targetBasis = Math.max(pb, cb);
    const targetDim = Math.max(parent.components.length, child.components.length);
    parent = upsampleSemanticVector(parent, targetBasis, targetDim);
    child = upsampleSemanticVector(child, targetBasis, targetDim);
    basisNote = `basis v${String(pb)} vs v${String(cb)} (upsampled to v${String(targetBasis)})`;
  }
  const pc = parent.components;
  const cc = child.components;
  const dim = Math.max(pc.length, cc.length);
  let l2Sq = 0;
  for (let i = 0; i < dim; i++) {
    const d = (i < cc.length ? cc[i]! : 0) - (i < pc.length ? pc[i]! : 0);
    l2Sq += d * d;
  }
  const l2 = Math.sqrt(l2Sq);
  let cosineDistance = vectorDistance(parent, child);
  if (cosineDistance < 0) {
    cosineDistance = 0;
  } else if (cosineDistance > 2) {
    cosineDistance = 2;
  }

  const t = params.thresholds;
  let l2Status: DivergenceStatus;
  if (l2 < t.l2StableMax) {
    l2Status = DS.STABLE;
  } else if (l2 >= t.l2DivergedMin) {
    l2Status = DS.DIVERGED;
  } else {
    l2Status = DS.DRIFTING;
  }

  let cosStatus: DivergenceStatus;
  if (cosineDistance < t.cosineStableMax) {
    cosStatus = DS.STABLE;
  } else if (cosineDistance >= t.cosineDivergedMin) {
    cosStatus = DS.DIVERGED;
  } else {
    cosStatus = DS.DRIFTING;
  }

  const rank = (s: DivergenceStatus) =>
    s === DS.STABLE ? 0 : s === DS.DRIFTING ? 1 : 2;
  const worst = rank(l2Status) > rank(cosStatus) ? l2Status : cosStatus;

  return {
    castId: params.castId,
    parentCastId: params.parentCastId,
    l2Magnitude: l2,
    cosineDistance,
    status: worst,
    computedAt: new Date(),
    basisNote,
  };
}
