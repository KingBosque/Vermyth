import { ulid } from "ulidx";

import type { Grimoire } from "../../grimoire/store.js";
import type { Intent } from "../../schema/intent.js";
import type { Aspect } from "../../schema/aspect.js";
import { aspectIdFromName } from "../../schema/aspect.js";
import type { CastResult } from "../../schema/cast-result.js";
import type { SemanticVector } from "../../schema/vectors.js";
import { defaultPolicyThresholds, type PolicyDecision, type PolicyThresholds } from "../../schema/policy.js";
import { DivergenceScorerPolicy, EffectRiskScorerPolicy, NarrativeScorerPolicy, ResonanceScorerPolicy } from "../policy/scorers.js";
import type { RuleBasedPolicyModel } from "../policy/rule-based.js";
import { classifyDivergenceReport } from "../../schema/divergence.js";
import type { DivergenceStatus } from "../../schema/enums.js";
import { defaultCausalQuery } from "../../schema/causal.js";
import type { ResonanceEngine } from "../resonance.js";
import * as casting from "./casting.js";
import { evaluateNarrative } from "./causal.js";

export function decide(
  engine: ResonanceEngine,
  policyModel: RuleBasedPolicyModel,
  intent: Intent,
  opts: {
    aspects?: ReadonlySet<Aspect> | null;
    vector?: SemanticVector | null;
    parentCastId?: string | null;
    causalRootCastId?: string | null;
    thresholds?: PolicyThresholds | null;
    grimoire?: Grimoire | null;
    effects?: unknown[] | null;
  },
): { decision: PolicyDecision; result: CastResult } {
  const thresholds = opts.thresholds ?? defaultPolicyThresholds();

  if (opts.aspects !== undefined && opts.aspects !== null && opts.vector !== undefined && opts.vector !== null) {
    throw new Error("pass either aspects or vector, not both");
  }

  let result: CastResult;
  if (opts.aspects !== undefined && opts.aspects !== null) {
    result = casting.cast(engine, opts.aspects, intent);
  } else if (opts.vector !== undefined && opts.vector !== null) {
    result = casting.fluidCast(engine, opts.vector, intent);
  } else {
    const seed = engine.buildIntentVector(intent).vector;
    const [r] = casting.autoCast(engine, seed, intent);
    result = r!;
  }

  let divergenceStatus: DivergenceStatus | null = null;
  if (opts.parentCastId !== undefined && opts.parentCastId !== null) {
    if (!opts.grimoire) {
      throw new Error("grimoire is required when parent_cast_id is provided");
    }
    const parent = opts.grimoire.casts.read(opts.parentCastId);
    const thr = opts.grimoire.readDivergenceThresholds();
    const report = classifyDivergenceReport({
      castId: result.castId,
      parentCastId: opts.parentCastId,
      parentVector: parent.sigil.semanticVector,
      childVector: result.sigil.semanticVector,
      thresholds: {
        l2StableMax: thr.l2StableMax,
        l2DivergedMin: thr.l2DivergedMin,
        cosineStableMax: thr.cosineStableMax,
        cosineDivergedMin: thr.cosineDivergedMin,
      },
    });
    divergenceStatus = report.status;
  }

  let narrativeCoherence: number | null = null;
  if (opts.causalRootCastId !== undefined && opts.causalRootCastId !== null) {
    if (!opts.grimoire) {
      throw new Error("grimoire is required when causal_root_cast_id is provided");
    }
    const graph = opts.grimoire.causalSubgraph(
      defaultCausalQuery({ rootCastId: opts.causalRootCastId }),
    );
    narrativeCoherence = evaluateNarrative(graph.edges);
  }

  const verdict = result.verdict.verdictType;
  const adjusted = result.verdict.resonance.adjusted;
  const weights = { ...thresholds.scorerWeights };
  const scorers = [
    new ResonanceScorerPolicy().score(adjusted, Number(weights["resonance"] ?? 0)),
    new DivergenceScorerPolicy().score(divergenceStatus, Number(weights["divergence"] ?? 0)),
    new NarrativeScorerPolicy().score(narrativeCoherence, Number(weights["narrative"] ?? 0)),
    new EffectRiskScorerPolicy().score(opts.effects ?? [], Number(weights["effect_risk"] ?? 0)),
  ];
  const totalWeight = scorers.reduce((a, s) => a + s.weight, 0) || 1;
  const aggregateScore =
    scorers.reduce((acc, s) => acc + s.value * s.weight, 0) / totalWeight;

  const { action, rationale } = policyModel.decide({
    verdict,
    adjustedResonance: adjusted,
    divergenceStatus,
    narrativeCoherence,
    scores: scorers,
    aggregateScore,
    thresholds,
  });

  const decision: PolicyDecision = {
    decisionId: ulid(),
    action,
    rationale,
    castId: result.castId,
    suggestedIntent: action === "RESHAPE" ? intent : null,
    parentCastId: opts.parentCastId ?? null,
    divergenceStatus,
    narrativeCoherence,
    thresholds,
    scores: scorers,
    explanation: `aggregate=${aggregateScore.toFixed(3)}; ${scorers.map((s) => `${s.name}=${s.value.toFixed(3)}`).join(", ")}`,
    modelName: policyModel.name,
    modelVersion: policyModel.version,
    timestamp: new Date(),
  };

  return { decision, result };
}

export function aspectSetFromNames(names: string[]): ReadonlySet<Aspect> {
  const s = new Set<Aspect>();
  for (const n of names) {
    s.add(aspectIdFromName(n));
  }
  return s;
}
