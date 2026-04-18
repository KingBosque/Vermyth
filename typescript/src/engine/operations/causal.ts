import type { CausalEdge } from "../../schema/causal.js";
import { CausalEdgeTypes } from "../../schema/causal.js";

/**
 * Narrative coherence from a set of causal edges (matches Python `evaluate_narrative`).
 */
export function evaluateNarrative(edges: readonly CausalEdge[]): number {
  if (edges.length === 0) {
    return 0;
  }
  const pairTypes = new Map<string, Set<string>>();
  let weightSum = 0;
  for (const edge of edges) {
    const key = `${edge.sourceCastId}\0${edge.targetCastId}`;
    let s = pairTypes.get(key);
    if (!s) {
      s = new Set();
      pairTypes.set(key, s);
    }
    s.add(edge.edgeType);
    weightSum += edge.weight;
  }
  let contradictions = 0;
  for (const types of pairTypes.values()) {
    if (types.has(CausalEdgeTypes.CAUSES) && types.has(CausalEdgeTypes.INHIBITS)) {
      contradictions += 1;
    }
  }
  const contradictionPenalty = Math.min(1, contradictions / Math.max(1, pairTypes.size));
  const avgWeight = weightSum / edges.length;
  const score = avgWeight * (1 - 0.5 * contradictionPenalty);
  return Math.max(0, Math.min(1, score));
}
