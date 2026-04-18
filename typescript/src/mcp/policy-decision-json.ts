import type { PolicyDecision } from "../schema/policy.js";

/** MCP / HTTP wire shape aligned with Python `policy_decision_to_dict`. */
export function policyDecisionToDict(decision: PolicyDecision): Record<string, unknown> {
  const ts = decision.timestamp ?? new Date();
  return {
    decision_id: decision.decisionId,
    action: decision.action,
    rationale: decision.rationale,
    cast_id: decision.castId,
    suggested_intent:
      decision.suggestedIntent === null
        ? null
        : {
            objective: decision.suggestedIntent.objective,
            scope: decision.suggestedIntent.scope,
            reversibility: decision.suggestedIntent.reversibility,
            side_effect_tolerance: decision.suggestedIntent.sideEffectTolerance,
          },
    parent_cast_id: decision.parentCastId,
    divergence_status: decision.divergenceStatus,
    narrative_coherence: decision.narrativeCoherence,
    thresholds: {
      allow_min_resonance: decision.thresholds.allowMinResonance,
      reshape_min_resonance: decision.thresholds.reshapeMinResonance,
      max_drift_status: decision.thresholds.maxDriftStatus,
      scorer_weights: decision.thresholds.scorerWeights,
      effect_risk_min_score: decision.thresholds.effectRiskMinScore,
    },
    scores: decision.scores.map((s) => ({
      name: s.name,
      value: s.value,
      weight: s.weight,
      explanation: s.explanation,
    })),
    explanation: decision.explanation,
    model_name: decision.modelName,
    model_version: decision.modelVersion,
    timestamp: ts.toISOString(),
  };
}
