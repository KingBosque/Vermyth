import type { ResonanceEngine } from "../../engine/resonance.js";
import type { AutoCastDiagnostics } from "../../engine/operations/casting.js";
import { autoCast, castAspectNames, fluidCast } from "../../engine/operations/casting.js";
import { decide, aspectSetFromNames } from "../../engine/operations/decisions.js";
import { evaluateNarrative } from "../../engine/operations/causal.js";
import { RuleBasedPolicyModel } from "../../engine/policy/rule-based.js";
import type { Intent } from "../../schema/intent.js";
import type { Aspect } from "../../schema/aspect.js";
import { aspectIdFromName } from "../../schema/aspect.js";
import type { Grimoire } from "../../grimoire/store.js";
import type { CastResult } from "../../schema/cast-result.js";
import { createSemanticVector } from "../../schema/vectors.js";
import { defaultSemanticQuery, type SemanticQuery } from "../../schema/semantic-query.js";
import { defaultPolicyThresholds, type PolicyThresholds } from "../../schema/policy.js";
import type { DivergenceStatus } from "../../schema/enums.js";
import { DivergenceStatus as DS } from "../../schema/enums.js";
import { defaultCausalQuery } from "../../schema/causal.js";
import { castResultToDict } from "../cast-result-json.js";
import { policyDecisionToDict } from "../policy-decision-json.js";
import type { EventBus } from "../../observability/event-bus.js";
import { AspectRegistry } from "../../registry.js";

function parseIntent(params: Record<string, unknown>): Intent {
  return {
    objective: String(params["objective"] ?? ""),
    scope: String(params["scope"] ?? ""),
    reversibility: params["reversibility"] as Intent["reversibility"],
    sideEffectTolerance: (params["side_effect_tolerance"] ?? params["sideEffectTolerance"]) as Intent["sideEffectTolerance"],
  };
}

function resolveIntentArg(args: Record<string, unknown>): Intent {
  const nested = args["intent"];
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    return parseIntent(nested as Record<string, unknown>);
  }
  return parseIntent(args);
}

function mergePolicyThresholds(raw: unknown): PolicyThresholds | null {
  if (raw === undefined || raw === null) {
    return null;
  }
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    return null;
  }
  const o = raw as Record<string, unknown>;
  const base = defaultPolicyThresholds();
  const sw = o["scorer_weights"];
  let scorerWeights = { ...base.scorerWeights };
  if (sw && typeof sw === "object" && !Array.isArray(sw)) {
    scorerWeights = { ...scorerWeights, ...(sw as Record<string, number>) };
  }
  return {
    allowMinResonance:
      typeof o["allow_min_resonance"] === "number" ? (o["allow_min_resonance"] as number) : base.allowMinResonance,
    reshapeMinResonance:
      typeof o["reshape_min_resonance"] === "number"
        ? (o["reshape_min_resonance"] as number)
        : base.reshapeMinResonance,
    maxDriftStatus: (() => {
      const v = o["max_drift_status"];
      if (v === DS.STABLE || v === DS.DRIFTING || v === DS.DIVERGED) {
        return v as DivergenceStatus;
      }
      if (typeof v === "string" && (Object.values(DS) as string[]).includes(v)) {
        return v as DivergenceStatus;
      }
      return base.maxDriftStatus;
    })(),
    scorerWeights,
    effectRiskMinScore:
      o["effect_risk_min_score"] === null || o["effect_risk_min_score"] === undefined
        ? base.effectRiskMinScore
        : (o["effect_risk_min_score"] as number | null),
  };
}

function parseSemanticQueryArgs(p: Record<string, unknown>): SemanticQuery {
  let aspectFilter: ReadonlySet<Aspect> | null | undefined;
  const af = p["aspect_filter"];
  if (Array.isArray(af)) {
    aspectFilter = new Set(af.map((x) => aspectIdFromName(String(x))));
  } else {
    aspectFilter = undefined;
  }
  const prox = p["proximity_to"];
  const proximityTo =
    Array.isArray(prox) && prox.length > 0 ? createSemanticVector(prox.map((x) => Number(x))) : null;
  return defaultSemanticQuery({
    aspectFilter: aspectFilter ?? null,
    verdictFilter: typeof p["verdict_filter"] === "string" ? (p["verdict_filter"] as SemanticQuery["verdictFilter"]) : null,
    minResonance: typeof p["min_resonance"] === "number" ? p["min_resonance"] : null,
    effectClassFilter:
      typeof p["effect_class_filter"] === "string" ? (p["effect_class_filter"] as SemanticQuery["effectClassFilter"]) : null,
    branchId: typeof p["branch_id"] === "string" ? p["branch_id"] : null,
    proximityTo,
    proximityThreshold: typeof p["proximity_threshold"] === "number" ? p["proximity_threshold"] : null,
    limit: typeof p["limit"] === "number" ? Math.floor(p["limit"]) : 20,
  });
}

export class VermythTools {
  private readonly policyModel = new RuleBasedPolicyModel();

  private toCastDict(result: CastResult): Record<string, unknown> {
    return castResultToDict(result, { grimoire: this.grimoire });
  }

  constructor(
    readonly engine: ResonanceEngine,
    readonly grimoire: Grimoire,
    readonly eventBus: EventBus | null = null,
  ) {}

  toolCast(params: Record<string, unknown>): Record<string, unknown> {
    const aspects = params["aspects"];
    if (!Array.isArray(aspects) || !aspects.every((x) => typeof x === "string")) {
      throw new Error("aspects must be an array of strings");
    }
    const intent = parseIntent(params);
    const result = castAspectNames(this.engine, aspects as string[], intent);
    try {
      this.grimoire.casts.write(result);
    } catch {
      /* optional persistence */
    }
    this.eventBus?.emit({
      name: "cast",
      payload: {
        aspects,
        verdict: result.verdict.verdictType,
        adjusted_resonance: result.verdict.resonance.adjusted,
      },
      castId: result.castId,
    });
    return this.toCastDict(result);
  }

  toolFluidCast(params: Record<string, unknown>): Record<string, unknown> {
    const raw = params["vector"];
    if (!Array.isArray(raw)) {
      throw new Error("vector must be an array of numbers");
    }
    const nums = raw.map((x) => Number(x));
    const intent = parseIntent(params);
    const vec = createSemanticVector(nums);
    const result = fluidCast(this.engine, vec, intent);
    try {
      this.grimoire.casts.write(result);
    } catch {
      /* optional */
    }
    return this.toCastDict(result);
  }

  toolDecide(params: Record<string, unknown>): Record<string, unknown> {
    const intent = resolveIntentArg(params);
    const aspectsRaw = params["aspects"];
    const vectorRaw = params["vector"];
    let aspects: ReadonlySet<Aspect> | null = null;
    let vector: ReturnType<typeof createSemanticVector> | null = null;
    if (Array.isArray(aspectsRaw) && aspectsRaw.length > 0 && aspectsRaw.every((x) => typeof x === "string")) {
      aspects = aspectSetFromNames(aspectsRaw as string[]);
    }
    if (Array.isArray(vectorRaw) && vectorRaw.length > 0) {
      vector = createSemanticVector(vectorRaw.map((x) => Number(x)));
    }
    if (aspects !== null && vector !== null) {
      throw new Error("pass either aspects or vector, not both");
    }
    const thresholds = mergePolicyThresholds(params["thresholds"]);
    const { decision, result } = decide(this.engine, this.policyModel, intent, {
      aspects,
      vector,
      parentCastId: typeof params["parent_cast_id"] === "string" ? params["parent_cast_id"] : null,
      causalRootCastId:
        typeof params["causal_root_cast_id"] === "string" ? params["causal_root_cast_id"] : null,
      thresholds,
      grimoire: this.grimoire,
      effects: Array.isArray(params["effects"]) ? params["effects"] : null,
    });
    try {
      this.grimoire.casts.write(result);
    } catch {
      /* idempotent optional */
    }
    try {
      this.grimoire.writePolicyDecision(decision);
    } catch {
      /* optional */
    }
    this.eventBus?.emit({
      name: "decide",
      payload: {
        action: decision.action,
        rationale: decision.rationale,
        cast_id: result.castId,
      },
      castId: result.castId,
    });
    return {
      decision: policyDecisionToDict(decision),
      cast: this.toCastDict(result),
    };
  }

  toolQueryCasts(params: Record<string, unknown>): Record<string, unknown> {
    const q = parseSemanticQueryArgs(params);
    const rows = this.grimoire.casts.query(q);
    return {
      casts: rows.map((r) => this.toCastDict(r)),
      count: rows.length,
    };
  }

  /** Python `semantic_search` tool — uses `proximity_vector` + `threshold`. */
  toolSemanticSearch(params: Record<string, unknown>): Record<string, unknown> {
    const pv = params["proximity_vector"];
    if (!Array.isArray(pv) || pv.length === 0) {
      throw new Error("proximity_vector must be a non-empty number array");
    }
    const threshold = typeof params["threshold"] === "number" ? params["threshold"] : 0.5;
    const limit = typeof params["limit"] === "number" ? Math.floor(params["limit"]) : 20;
    const q = defaultSemanticQuery({
      proximityTo: createSemanticVector(pv.map((x) => Number(x))),
      proximityThreshold: threshold,
      limit,
    });
    const rows = this.grimoire.casts.semanticSearch(q);
    return { casts: rows.map((r) => this.toCastDict(r)) };
  }

  toolInspect(params: Record<string, unknown>): Record<string, unknown> {
    const id = String(params["cast_id"] ?? "");
    if (!id) {
      throw new Error("cast_id is required");
    }
    return this.toCastDict(this.grimoire.read(id));
  }

  toolLineage(params: Record<string, unknown>): Record<string, unknown> {
    const id = String(params["cast_id"] ?? "");
    if (!id) {
      throw new Error("cast_id is required");
    }
    const maxDepth = typeof params["max_depth"] === "number" ? params["max_depth"] : 50;
    const chainRev: CastResult[] = [];
    let curId: string | null = id;
    for (let i = 0; i < maxDepth && curId !== null; i++) {
      const row = this.grimoire.read(curId);
      chainRev.push(row);
      curId = row.lineage?.parentCastId ?? null;
    }
    const chain = chainRev.slice().reverse();
    return { casts: chain.map((r) => this.toCastDict(r)) };
  }

  toolAutoCast(params: Record<string, unknown>): Record<string, unknown> {
    const raw = params["vector"];
    if (!Array.isArray(raw)) {
      throw new Error("vector must be an array of numbers");
    }
    const vec = createSemanticVector(raw.map((x) => Number(x)));
    const intent = parseIntent(params);
    const maxDepth = typeof params["max_depth"] === "number" ? params["max_depth"] : 5;
    const targetResonance = typeof params["target_resonance"] === "number" ? params["target_resonance"] : 0.75;
    const blendAlpha = typeof params["blend_alpha"] === "number" ? params["blend_alpha"] : 0.35;
    const includeDiagnostics = Boolean(params["include_diagnostics"]);
    const out = autoCast(this.engine, vec, intent, {
      maxDepth,
      targetResonance,
      blendAlpha,
      withDiagnostics: includeDiagnostics,
    });
    if (includeDiagnostics && out.length === 3) {
      const [result, chain, diag] = out as [CastResult, CastResult[], AutoCastDiagnostics];
      try {
        this.grimoire.casts.write(result);
      } catch {
        /* optional */
      }
      return {
        cast: this.toCastDict(result),
        chain: chain.map((c) => this.toCastDict(c)),
        diagnostics: diag,
      };
    }
    const [result, chain] = out as [CastResult, CastResult[]];
    try {
      this.grimoire.casts.write(result);
    } catch {
      /* optional */
    }
    return {
      cast: this.toCastDict(result),
      chain: chain.map((c) => this.toCastDict(c)),
    };
  }

  toolCausalSubgraph(params: Record<string, unknown>): Record<string, unknown> {
    const root = String(params["root_cast_id"] ?? "");
    if (!root) {
      throw new Error("root_cast_id is required");
    }
    const edgeTypes = Array.isArray(params["edge_types"])
      ? (params["edge_types"] as string[]).map((x) => String(x))
      : null;
    const direction = (params["direction"] === "forward" || params["direction"] === "backward"
      ? params["direction"]
      : "both") as "forward" | "backward" | "both";
    const maxDepth = typeof params["max_depth"] === "number" ? params["max_depth"] : 5;
    const minWeight = typeof params["min_weight"] === "number" ? params["min_weight"] : 0;
    const graph = this.grimoire.causalSubgraph(
      defaultCausalQuery({
        rootCastId: root,
        edgeTypes: edgeTypes as import("../../schema/causal.js").CausalEdgeType[] | null,
        direction,
        maxDepth,
        minWeight,
      }),
    );
    return {
      root_cast_id: graph.rootCastId,
      nodes: graph.nodes,
      edges: graph.edges.map((e) => ({
        edge_id: e.edgeId,
        source_cast_id: e.sourceCastId,
        target_cast_id: e.targetCastId,
        edge_type: e.edgeType,
        weight: e.weight,
        created_at: e.createdAt.toISOString(),
        evidence: e.evidence,
      })),
      narrative_coherence: graph.narrativeCoherence,
    };
  }

  toolEvaluateNarrative(params: Record<string, unknown>): Record<string, unknown> {
    const ids = params["edge_ids"];
    if (!Array.isArray(ids)) {
      throw new Error("edge_ids must be an array");
    }
    const edges = ids.map((id) => this.grimoire.readCausalEdge(String(id)));
    const score = evaluateNarrative(edges);
    return { narrative_coherence: score, edge_count: edges.length };
  }

  toolRegisteredAspects(_params: Record<string, unknown>): Record<string, unknown> {
    const aspects = this.grimoire
      .queryRegisteredAspects()
      .map(([a, ordinal]) => ({ name: a.name, ordinal, symbol: a.symbol, polarity: a.polarity }));
    return {
      basis_version: AspectRegistry.get().getBasisVersion(),
      aspects,
    };
  }

  toolRegisteredSigils(_params: Record<string, unknown>): Record<string, unknown> {
    return { sigils: this.grimoire.queryRegisteredSigils() };
  }

  toolRecordEvent(params: Record<string, unknown>): Record<string, unknown> {
    const name = String(params["name"] ?? "event");
    const payload =
      params["payload"] && typeof params["payload"] === "object" && !Array.isArray(params["payload"])
        ? (params["payload"] as Record<string, unknown>)
        : {};
    this.eventBus?.emit({
      name,
      payload,
      castId: typeof params["cast_id"] === "string" ? params["cast_id"] : null,
    });
    return { ok: true };
  }

  toolEventsTail(params: Record<string, unknown>): Record<string, unknown> {
    const n = typeof params["n"] === "number" ? params["n"] : 100;
    const eventType = typeof params["event_type"] === "string" ? params["event_type"] : null;
    if (!this.eventBus) {
      return { events: [] };
    }
    const events = this.eventBus.tail(n, eventType).map((e) => ({
      name: e.name,
      payload: e.payload,
      cast_id: e.castId ?? null,
      branch_id: e.branchId ?? null,
    }));
    return { events };
  }

  toolListPrograms(params: Record<string, unknown>): Record<string, unknown> {
    const limit = typeof params["limit"] === "number" ? params["limit"] : 50;
    const rows = this.grimoire.listPrograms(limit);
    return {
      programs: rows.map((p) => ({
        program_id: p.program_id,
        name: p.name,
        status: p.status,
        created_at: p.created_at,
        updated_at: p.updated_at,
      })),
      count: rows.length,
    };
  }

  toolDriftBranches(params: Record<string, unknown>): Record<string, unknown> {
    const limit = typeof params["limit"] === "number" ? params["limit"] : 25;
    return { branches: this.grimoire.driftBranches(limit) };
  }

  toolSwarmStatus(_params: Record<string, unknown>): Record<string, unknown> {
    return {
      success: false,
      code: "NOT_PORTED_IN_TYPESCRIPT",
      surface: "swarm",
      peers: [],
    };
  }

  toolGossipSync(_params: Record<string, unknown>): Record<string, unknown> {
    return {
      success: false,
      code: "NOT_PORTED_IN_TYPESCRIPT",
      surface: "gossip_sync",
    };
  }

  toolSwarmCast(_params: Record<string, unknown>): Record<string, unknown> {
    return {
      success: false,
      code: "NOT_PORTED_IN_TYPESCRIPT",
      surface: "swarm_cast",
    };
  }

  toolSwarmJoin(_params: Record<string, unknown>): Record<string, unknown> {
    return {
      success: false,
      code: "NOT_PORTED_IN_TYPESCRIPT",
      surface: "swarm_join",
    };
  }
}
