import { describe, expect, it } from "vitest";

import { evaluateNarrative } from "./causal.js";
import type { CausalEdge } from "../../schema/causal.js";
import { CausalEdgeTypes } from "../../schema/causal.js";

function edge(
  source: string,
  target: string,
  type: (typeof CausalEdgeTypes)[keyof typeof CausalEdgeTypes],
  weight: number,
): CausalEdge {
  return {
    edgeId: `${source}->${target}`,
    sourceCastId: source,
    targetCastId: target,
    edgeType: type,
    weight,
    createdAt: new Date(),
    evidence: null,
  };
}

describe("evaluateNarrative", () => {
  it("returns 0 for empty edges", () => {
    expect(evaluateNarrative([])).toBe(0);
  });

  it("penalizes CAUSES+INHIBITS on the same pair", () => {
    const a = edge("a", "b", CausalEdgeTypes.CAUSES, 0.8);
    const b = edge("a", "b", CausalEdgeTypes.INHIBITS, 0.8);
    const s = evaluateNarrative([a, b]);
    expect(s).toBeGreaterThanOrEqual(0);
    expect(s).toBeLessThan(0.8);
  });
});
