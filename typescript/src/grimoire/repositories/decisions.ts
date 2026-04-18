import BetterSqlite3 from "better-sqlite3";

import type { PolicyDecision } from "../../schema/policy.js";

type SqliteDb = InstanceType<typeof BetterSqlite3>;

function thresholdsToJson(t: PolicyDecision["thresholds"]): string {
  return JSON.stringify({
    allow_min_resonance: t.allowMinResonance,
    reshape_min_resonance: t.reshapeMinResonance,
    max_drift_status: t.maxDriftStatus,
    scorer_weights: t.scorerWeights,
    effect_risk_min_score: t.effectRiskMinScore,
  });
}

export class DecisionRepository {
  constructor(private readonly db: SqliteDb) {}

  writePolicyDecision(decision: PolicyDecision): void {
    const ts = decision.timestamp ?? new Date();
    this.db
      .prepare(
        `
      INSERT OR REPLACE INTO policy_decisions (
        decision_id, action, cast_id, parent_cast_id, divergence_status,
        narrative_coherence, thresholds_json, rationale, suggested_intent_json,
        policy_model_name, policy_model_version, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
      )
      .run(
        decision.decisionId,
        decision.action,
        decision.castId,
        decision.parentCastId,
        decision.divergenceStatus,
        decision.narrativeCoherence,
        thresholdsToJson(decision.thresholds),
        decision.rationale,
        decision.suggestedIntent
          ? JSON.stringify({
              objective: decision.suggestedIntent.objective,
              scope: decision.suggestedIntent.scope,
              reversibility: decision.suggestedIntent.reversibility,
              side_effect_tolerance: decision.suggestedIntent.sideEffectTolerance,
            })
          : null,
        decision.modelName,
        decision.modelVersion,
        ts.toISOString(),
      );
  }
}
