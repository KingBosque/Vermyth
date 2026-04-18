import type { CompositionEngine } from "../engine/composition.js";
import type { ResonanceEngine } from "../engine/resonance.js";

export interface CompositionContract {
  compose: CompositionEngine["compose"];
}

export interface EvaluationContract {
  evaluate: ResonanceEngine["evaluate"];
}
