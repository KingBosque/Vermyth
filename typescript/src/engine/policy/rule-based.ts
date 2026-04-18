import type { DivergenceStatus } from "../../schema/enums.js";
import { DivergenceStatus as DS } from "../../schema/enums.js";
import type { VerdictType } from "../../schema/enums.js";
import { VerdictType as VT } from "../../schema/enums.js";
import type { PolicyAction } from "../../schema/policy.js";
import type { PolicyThresholds } from "../../schema/policy.js";
import type { ScoreComponent } from "../../schema/policy.js";

export class RuleBasedPolicyModel {
  readonly name = "rule_based";
  readonly version = "1";

  decide(params: {
    verdict: VerdictType;
    adjustedResonance: number;
    divergenceStatus: DivergenceStatus | null;
    narrativeCoherence: number | null;
    scores: ScoreComponent[];
    aggregateScore: number;
    thresholds: PolicyThresholds;
  }): { action: PolicyAction; rationale: string } {
    const { verdict, adjustedResonance, divergenceStatus, scores, aggregateScore, thresholds } =
      params;
    const driftOk =
      divergenceStatus === null ||
      divergenceStatus === DS.STABLE ||
      divergenceStatus === thresholds.maxDriftStatus;

    const effectSc = scores.find((c) => c.name === "effect_risk");
    if (
      thresholds.effectRiskMinScore !== null &&
      effectSc !== undefined &&
      effectSc.weight > 0 &&
      effectSc.value < thresholds.effectRiskMinScore
    ) {
      return {
        action: "DENY",
        rationale: `verdict=${verdict}; effect_risk=${effectSc.value.toFixed(3)} below min ${thresholds.effectRiskMinScore.toFixed(3)}; ${effectSc.explanation}`,
      };
    }

    let action: PolicyAction;
    if (verdict === VT.INCOHERENT || divergenceStatus === DS.DIVERGED) {
      action = "DENY";
    } else if (
      verdict === VT.COHERENT &&
      adjustedResonance >= thresholds.allowMinResonance &&
      driftOk &&
      aggregateScore >= thresholds.allowMinResonance
    ) {
      action = "ALLOW";
    } else {
      action = "RESHAPE";
    }

    const parts = [
      `verdict=${verdict}`,
      `resonance=${adjustedResonance.toFixed(3)}`,
    ];
    if (divergenceStatus !== null) {
      parts.push(`drift=${divergenceStatus}`);
    }
    if (params.narrativeCoherence !== null && params.narrativeCoherence !== undefined) {
      parts.push(`narrative=${params.narrativeCoherence.toFixed(3)}`);
    }
    parts.push(`aggregate=${aggregateScore.toFixed(3)}`);
    parts.push(...scores.map((c) => `${c.name}:${c.value.toFixed(3)}x${c.weight.toFixed(2)}`));
    parts.push(`decision=${action}`);
    return { action, rationale: parts.join("; ") };
  }
}
