export const CausalEdgeTypes = {
  CAUSES: "CAUSES",
  INHIBITS: "INHIBITS",
  ENABLES: "ENABLES",
  REQUIRES: "REQUIRES",
} as const;
export type CausalEdgeType = (typeof CausalEdgeTypes)[keyof typeof CausalEdgeTypes];

export interface CausalEdge {
  readonly edgeId: string;
  readonly sourceCastId: string;
  readonly targetCastId: string;
  readonly edgeType: CausalEdgeType;
  readonly weight: number;
  readonly createdAt: Date;
  readonly evidence: string | null;
}

export interface CausalQuery {
  readonly rootCastId: string;
  readonly edgeTypes?: readonly CausalEdgeType[] | null;
  readonly direction: "forward" | "backward" | "both";
  readonly maxDepth: number;
  readonly minWeight: number;
}

export function defaultCausalQuery(
  overrides: Partial<Omit<CausalQuery, "rootCastId">> & { rootCastId: string },
): CausalQuery {
  return {
    edgeTypes: null,
    direction: "both",
    maxDepth: 5,
    minWeight: 0,
    ...overrides,
  };
}

export interface CausalSubgraph {
  readonly rootCastId: string;
  readonly nodes: readonly string[];
  readonly edges: readonly CausalEdge[];
  readonly narrativeCoherence: number;
}
