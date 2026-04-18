/**
 * MCP tool metadata aligned with `vermyth/mcp/tool_definitions.py`.
 * Runtime list may append experimental tools when `VERMYTH_EXPERIMENTAL_TOOLS` is set.
 */

const intentProps = {
  objective: { type: "string" },
  scope: { type: "string" },
  reversibility: { type: "string", enum: ["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"] },
  side_effect_tolerance: { type: "string", enum: ["NONE", "LOW", "MEDIUM", "HIGH"] },
};

export const TOOL_DEFINITIONS_BASE: Array<Record<string, unknown>> = [
  {
    name: "decide",
    description: "Run a cast policy decision and return ALLOW/RESHAPE/DENY with rationale.",
    inputSchema: {
      type: "object",
      properties: {
        intent: { type: "object", properties: intentProps, required: Object.keys(intentProps) },
        aspects: { type: "array", items: { type: "string" } },
        vector: { type: "array", items: { type: "number" } },
        parent_cast_id: { type: "string" },
        causal_root_cast_id: { type: "string" },
        thresholds: { type: "object" },
        effects: { type: "array", items: { type: "object" } },
      },
      required: ["intent"],
    },
  },
  {
    name: "cast",
    description: "Compose aspects into a Sigil and evaluate against a declared Intent.",
    inputSchema: {
      type: "object",
      properties: {
        aspects: { type: "array", items: { type: "string" } },
        ...intentProps,
      },
      required: ["aspects", "objective", "scope", "reversibility", "side_effect_tolerance"],
    },
  },
  {
    name: "fluid_cast",
    description: "Interpolate a FluidSigil from a raw semantic vector and evaluate.",
    inputSchema: {
      type: "object",
      properties: {
        vector: { type: "array", items: { type: "number" } },
        ...intentProps,
      },
      required: ["vector", "objective", "scope", "reversibility", "side_effect_tolerance"],
    },
  },
  {
    name: "auto_cast",
    description: "Iteratively blend toward coherence using fluid_cast until resonance threshold.",
    inputSchema: {
      type: "object",
      properties: {
        vector: { type: "array", items: { type: "number" } },
        max_depth: { type: "number" },
        target_resonance: { type: "number" },
        blend_alpha: { type: "number" },
        include_diagnostics: { type: "boolean" },
        ...intentProps,
      },
      required: ["vector", "objective", "scope", "reversibility", "side_effect_tolerance"],
    },
  },
  {
    name: "inspect",
    description: "Retrieve a single CastResult by cast_id.",
    inputSchema: {
      type: "object",
      properties: { cast_id: { type: "string" } },
      required: ["cast_id"],
    },
  },
  {
    name: "lineage",
    description: "Walk the parent chain from a cast_id (root-first).",
    inputSchema: {
      type: "object",
      properties: {
        cast_id: { type: "string" },
        max_depth: { type: "integer" },
      },
      required: ["cast_id"],
    },
  },
  {
    name: "query",
    description: "Query the grimoire for CastResults by field filters.",
    inputSchema: {
      type: "object",
      properties: {
        aspect_filter: { type: "array", items: { type: "string" } },
        verdict_filter: { type: "string", enum: ["COHERENT", "PARTIAL", "INCOHERENT"] },
        min_resonance: { type: "number" },
        effect_class_filter: { type: "string" },
        branch_id: { type: "string" },
        proximity_to: { type: "array", items: { type: "number" } },
        proximity_threshold: { type: "number" },
        limit: { type: "integer" },
      },
    },
  },
  {
    name: "semantic_search",
    description: "Search by semantic proximity to a vector.",
    inputSchema: {
      type: "object",
      properties: {
        proximity_vector: { type: "array", items: { type: "number" } },
        threshold: { type: "number" },
        limit: { type: "integer" },
      },
      required: ["proximity_vector", "threshold"],
    },
  },
  {
    name: "causal_subgraph",
    description: "Expand a causal subgraph from a root cast id.",
    inputSchema: {
      type: "object",
      properties: {
        root_cast_id: { type: "string" },
        edge_types: { type: "array", items: { type: "string" } },
        direction: { type: "string", enum: ["forward", "backward", "both"] },
        max_depth: { type: "integer" },
        min_weight: { type: "number" },
      },
      required: ["root_cast_id"],
    },
  },
  {
    name: "evaluate_narrative",
    description: "Score narrative coherence for a list of causal edge ids.",
    inputSchema: {
      type: "object",
      properties: { edge_ids: { type: "array", items: { type: "string" } } },
      required: ["edge_ids"],
    },
  },
  {
    name: "registered_aspects",
    description: "List registered Aspects (non-canonical).",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "registered_sigils",
    description: "List registered Sigils (overrides/extensions).",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "list_programs",
    description: "List semantic programs (stub in TypeScript).",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "drift_branches",
    description: "List drift branches (stub in TypeScript).",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "record_event",
    description: "Record an observability event on the in-process bus.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string" },
        payload: { type: "object" },
        cast_id: { type: "string" },
      },
      required: ["name"],
    },
  },
  {
    name: "events_tail",
    description: "Read recent observability events emitted by Vermyth.",
    inputSchema: {
      type: "object",
      properties: {
        n: { type: "integer" },
        event_type: { type: "string" },
      },
    },
  },
];

export const TOOL_DEFINITIONS_EXPERIMENTAL: Array<Record<string, unknown>> = [
  {
    name: "gossip_sync",
    description: "Apply a signed federation gossip payload (stub).",
    inputSchema: { type: "object", properties: { peer_id: { type: "string" }, proof: { type: "string" } } },
  },
  {
    name: "swarm_cast",
    description: "Swarm consensus cast (stub).",
    inputSchema: {
      type: "object",
      properties: {
        swarm_id: { type: "string" },
        session_id: { type: "string" },
        vector: { type: "array", items: { type: "number" } },
        ...intentProps,
      },
      required: ["swarm_id", "session_id", "vector", "objective", "scope", "reversibility", "side_effect_tolerance"],
    },
  },
  {
    name: "swarm_join",
    description: "Join or create a swarm channel (stub).",
    inputSchema: { type: "object", properties: { swarm_id: { type: "string" } }, required: ["swarm_id"] },
  },
];
