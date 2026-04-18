import type { VermythTools } from "./tools/facade.js";
import { TOOL_DEFINITIONS_BASE, TOOL_DEFINITIONS_EXPERIMENTAL } from "./tool-definitions.js";

export type ToolHandler = (tools: VermythTools, args: Record<string, unknown>) => unknown;

export function isExperimentalToolsEnabled(): boolean {
  return /^(1|true|yes)$/i.test(process.env.VERMYTH_EXPERIMENTAL_TOOLS ?? "0");
}

export function getToolDefinitions(): Array<Record<string, unknown>> {
  return isExperimentalToolsEnabled()
    ? [...TOOL_DEFINITIONS_BASE, ...TOOL_DEFINITIONS_EXPERIMENTAL]
    : [...TOOL_DEFINITIONS_BASE];
}

export function createToolDispatch(): Record<string, ToolHandler> {
  const d: Record<string, ToolHandler> = {
    cast: (t, a) => t.toolCast(a),
    fluid_cast: (t, a) => t.toolFluidCast(a),
    decide: (t, a) => t.toolDecide(a),
    query: (t, a) => t.toolQueryCasts(a),
    semantic_search: (t, a) => t.toolSemanticSearch(a),
    inspect: (t, a) => t.toolInspect(a),
    lineage: (t, a) => t.toolLineage(a),
    auto_cast: (t, a) => t.toolAutoCast(a),
    causal_subgraph: (t, a) => t.toolCausalSubgraph(a),
    evaluate_narrative: (t, a) => t.toolEvaluateNarrative(a),
    registered_aspects: (t, a) => t.toolRegisteredAspects(a),
    registered_sigils: (t, a) => t.toolRegisteredSigils(a),
    list_programs: (t, a) => t.toolListPrograms(a),
    drift_branches: (t, a) => t.toolDriftBranches(a),
    record_event: (t, a) => t.toolRecordEvent(a),
    events_tail: (t, a) => t.toolEventsTail(a),
  };
  if (isExperimentalToolsEnabled()) {
    d["gossip_sync"] = (t, a) => t.toolGossipSync(a);
    d["swarm_cast"] = (t, a) => t.toolSwarmCast(a);
    d["swarm_join"] = (t, a) => t.toolSwarmJoin(a);
  }
  return d;
}
