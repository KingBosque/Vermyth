import type { DivergenceStatus } from "./enums.js";
import type { Intent } from "./intent.js";

export interface PolicyThresholds {
  allowMinResonance: number;
  reshapeMinResonance: number;
  maxDriftStatus: DivergenceStatus;
  scorerWeights: Record<string, number>;
  effectRiskMinScore: number | null;
}

export const defaultPolicyThresholds = (): PolicyThresholds => ({
  allowMinResonance: 0.75,
  reshapeMinResonance: 0.45,
  maxDriftStatus: "DRIFTING",
  scorerWeights: {
    resonance: 0.5,
    divergence: 0.2,
    narrative: 0.1,
    effect_risk: 0.2,
  },
  effectRiskMinScore: null,
});

export interface ScoreComponent {
  name: string;
  value: number;
  weight: number;
  explanation: string;
}

export type PolicyAction = "ALLOW" | "RESHAPE" | "DENY";

export interface PolicyDecision {
  decisionId: string;
  action: PolicyAction;
  rationale: string;
  castId: string;
  suggestedIntent: Intent | null;
  parentCastId: string | null;
  divergenceStatus: DivergenceStatus | null;
  narrativeCoherence: number | null;
  thresholds: PolicyThresholds;
  scores: ScoreComponent[];
  explanation: string | null;
  modelName: string;
  modelVersion: string | null;
  /** When persisted or returned over MCP; mirrors Python `PolicyDecision.timestamp`. */
  timestamp?: Date;
}
