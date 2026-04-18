import type { DivergenceStatus } from "../../schema/enums.js";
import type { ScoreComponent } from "../../schema/policy.js";

export class ResonanceScorerPolicy {
  score(adjustedResonance: number, weight: number): ScoreComponent {
    const v = Math.max(0, Math.min(1, adjustedResonance));
    return {
      name: "resonance",
      value: v,
      weight,
      explanation: `adjusted resonance ${adjustedResonance.toFixed(3)}`,
    };
  }
}

export class DivergenceScorerPolicy {
  score(divergenceStatus: DivergenceStatus | null | undefined, weight: number): ScoreComponent {
    let v = 0.5;
    if (divergenceStatus === "STABLE") {
      v = 1;
    } else if (divergenceStatus === "DRIFTING") {
      v = 0.5;
    } else if (divergenceStatus === "DIVERGED") {
      v = 0;
    }
    return {
      name: "divergence",
      value: v,
      weight,
      explanation: divergenceStatus ? `drift ${divergenceStatus}` : "no parent drift",
    };
  }
}

export class NarrativeScorerPolicy {
  score(narrativeCoherence: number | null | undefined, weight: number): ScoreComponent {
    const v =
      narrativeCoherence === null || narrativeCoherence === undefined
        ? 0.5
        : Math.max(0, Math.min(1, narrativeCoherence));
    return {
      name: "narrative",
      value: v,
      weight,
      explanation: "narrative coherence",
    };
  }
}

export class EffectRiskScorerPolicy {
  score(_effects: unknown[], weight: number): ScoreComponent {
    return {
      name: "effect_risk",
      value: 1,
      weight,
      explanation: "effect risk placeholder (full parity requires Effect model)",
    };
  }
}
