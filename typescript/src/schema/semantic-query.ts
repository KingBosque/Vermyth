import type { Aspect } from "./aspect.js";
import type { EffectClass } from "./enums.js";
import type { VerdictType } from "./enums.js";
import type { SemanticVector } from "./vectors.js";

export interface SemanticQuery {
  aspectFilter?: ReadonlySet<Aspect> | null;
  verdictFilter?: VerdictType | null;
  minResonance?: number | null;
  effectClassFilter?: EffectClass | null;
  branchId?: string | null;
  proximityTo?: SemanticVector | null;
  proximityThreshold?: number | null;
  limit: number;
}

export function defaultSemanticQuery(overrides?: Partial<SemanticQuery>): SemanticQuery {
  return {
    limit: 20,
    ...overrides,
  };
}
