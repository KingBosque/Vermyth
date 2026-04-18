import type {
  ProjectionMethod,
  ReversibilityClass,
  SideEffectTolerance,
} from "./enums.js";
import { ProjectionMethod as PM } from "./enums.js";
import type { SemanticVector } from "./vectors.js";
import { createSemanticVector } from "./vectors.js";

export interface Intent {
  objective: string;
  scope: string;
  reversibility: ReversibilityClass;
  sideEffectTolerance: SideEffectTolerance;
}

export interface IntentVector {
  vector: SemanticVector;
  projectionMethod: ProjectionMethod;
  constraintComponent: SemanticVector;
  semanticComponent: SemanticVector | null;
  confidence: number;
}

export function createIntentVector(params: {
  vector: SemanticVector;
  projectionMethod: ProjectionMethod;
  constraintComponent: SemanticVector;
  semanticComponent: SemanticVector | null;
  confidence: number;
}): IntentVector {
  if (params.projectionMethod === PM.FULL && params.semanticComponent === null) {
    throw new Error("semantic_component is required when projection_method is FULL");
  }
  if (params.projectionMethod === PM.PARTIAL && params.confidence > 0.65) {
    throw new Error("confidence must be at most 0.65 when projection_method is PARTIAL");
  }
  return {
    vector: params.vector,
    projectionMethod: params.projectionMethod,
    constraintComponent: params.constraintComponent,
    semanticComponent: params.semanticComponent,
    confidence: params.confidence,
  };
}

export function fallbackIntentVector(dim: number): IntentVector {
  const z = createSemanticVector(Array(dim).fill(0), null);
  return createIntentVector({
    vector: z,
    projectionMethod: PM.PARTIAL,
    constraintComponent: z,
    semanticComponent: null,
    confidence: 0.6,
  });
}
