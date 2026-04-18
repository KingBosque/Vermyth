import type { SemanticVector } from "./vectors.js";

export interface Lineage {
  parentCastId: string;
  depth: number;
  branchId: string;
  divergenceVector?: SemanticVector | null;
}
