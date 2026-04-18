import type { CompositionEngine } from "./composition.js";
import type { ProjectionBackend } from "./projection.js";
import * as castOps from "./operations/cast-ops.js";
import * as intentOps from "./operations/intent-ops.js";
import * as casting from "./operations/casting.js";
import { decide as engineDecide } from "./operations/decisions.js";
import { evaluateNarrative as scoreNarrative } from "./operations/causal.js";
import { RuleBasedPolicyModel } from "./policy/rule-based.js";
import type { Intent } from "../schema/intent.js";
import type { IntentVector } from "../schema/intent.js";
import type { Aspect } from "../schema/aspect.js";
import type { SemanticVector } from "../schema/vectors.js";
import type { PolicyDecision, PolicyThresholds } from "../schema/policy.js";
import type { CausalEdge } from "../schema/causal.js";
import type { Grimoire } from "../grimoire/store.js";
import type { FluidSigil, Sigil } from "../schema/sigil.js";
import type { Verdict } from "../schema/verdict.js";
import type { CastResult } from "../schema/cast-result.js";
import type { CastEngineLike } from "./operations/cast-ops.js";
import type { IntentEngineLike } from "./operations/intent-ops.js";

/**
 * Mirrors Python `ResonanceEngine` entry points: thin delegates over `operations/*`
 * so callers can use `engine.cast` / `engine.decide` / `engine.evaluate_narrative`.
 */
export class ResonanceEngine implements CastEngineLike, IntentEngineLike {
  contradictions: Record<string, Record<string, unknown>> | null;
  readonly policyModel: RuleBasedPolicyModel;

  constructor(
    readonly compositionEngine: CompositionEngine,
    readonly backend: ProjectionBackend | null = null,
    contradictions?: Record<string, Record<string, unknown>> | null,
    policyModel?: RuleBasedPolicyModel | null,
  ) {
    this.contradictions = contradictions ?? compositionEngine.contradictionsMap;
    this.policyModel = policyModel ?? new RuleBasedPolicyModel();
  }

  cast(aspects: ReadonlySet<Aspect>, intent: Intent): CastResult {
    return casting.cast(this, aspects, intent);
  }

  fluidCast(vector: SemanticVector, intent: Intent): CastResult {
    return casting.fluidCast(this, vector, intent);
  }

  autoCast(
    vector: SemanticVector,
    intent: Intent,
    opts?: Parameters<typeof casting.autoCast>[3],
  ): ReturnType<typeof casting.autoCast> {
    return casting.autoCast(this, vector, intent, opts);
  }

  decide(
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
    return engineDecide(this, this.policyModel, intent, opts);
  }

  evaluateNarrative(edges: readonly CausalEdge[]): number {
    return scoreNarrative(edges);
  }

  clipComponent(x: number): number {
    return intentOps.clipComponent(x);
  }

  normalizeUnit(components: readonly number[]): import("../schema/vectors.js").SemanticVector {
    return intentOps.normalizeUnit(components);
  }

  buildIntentVector(intent: Intent): IntentVector {
    return intentOps.buildIntentVector(this, intent);
  }

  computeResonance(sigil: Sigil | FluidSigil, intentVector: IntentVector) {
    return castOps.computeResonance(this, sigil, intentVector);
  }

  verdictType(adjusted: number) {
    return castOps.verdictType(adjusted);
  }

  castingNote(
    sigil: Sigil | FluidSigil,
    vt: import("../schema/enums.js").VerdictType,
    intentVector: IntentVector,
  ): string {
    return castOps.castingNote(sigil, vt, intentVector);
  }

  effectDescription(sigil: Sigil | FluidSigil, vt: import("../schema/enums.js").VerdictType): string {
    return castOps.effectDescription(sigil, vt);
  }

  incoherenceReason(
    sigil: Sigil | FluidSigil,
    vt: import("../schema/enums.js").VerdictType,
    cosine: number,
  ): string | null {
    return castOps.incoherenceReason(this, sigil, vt, cosine);
  }

  evaluate(sigil: Sigil | FluidSigil, intent: Intent): Verdict {
    return castOps.evaluate(this, sigil, intent);
  }
}
