import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { policyDecisionToDict } from "./policy-decision-json.js";
import { ReversibilityClass, SideEffectTolerance } from "../schema/enums.js";
import { defaultPolicyThresholds, type PolicyDecision } from "../schema/policy.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

function buildGoldenPolicyDecision(): PolicyDecision {
  return {
    decisionId: "01JDECISIONABCDEFGHJKMNPQR",
    action: "ALLOW",
    rationale: "Golden parity: coherent cast above allow threshold.",
    castId: "01HZX8Q4K9ABCDEFGHJKMNPQRS",
    suggestedIntent: null,
    parentCastId: null,
    divergenceStatus: null,
    narrativeCoherence: null,
    thresholds: defaultPolicyThresholds(),
    scores: [
      { name: "resonance", value: 0.82, weight: 0.5, explanation: "adjusted resonance 0.820" },
      { name: "divergence", value: 1, weight: 0.2, explanation: "divergence stable" },
      { name: "narrative", value: 0.5, weight: 0.1, explanation: "narrative n/a" },
      { name: "effect_risk", value: 0.9, weight: 0.2, explanation: "effect risk ok" },
    ],
    explanation:
      "aggregate=0.500; resonance=0.820, divergence=1.000, narrative=0.500, effect_risk=0.900",
    modelName: "rule_based",
    modelVersion: "1",
    timestamp: new Date("2024-06-15T10:00:00.000Z"),
  };
}

function buildGoldenPolicyDecisionReshape(): PolicyDecision {
  return {
    decisionId: "01JRESHAPEABCDEFGHJKMNOPQ1",
    action: "RESHAPE",
    rationale: "Golden parity: partial coherence; suggest intent refinement.",
    castId: "01HZX8Q4K9ABCDEFGHJKMNPQR2",
    suggestedIntent: {
      objective: "Refined objective for reshape",
      scope: "golden reshape scope",
      reversibility: ReversibilityClass.PARTIAL,
      sideEffectTolerance: SideEffectTolerance.MEDIUM,
    },
    parentCastId: null,
    divergenceStatus: null,
    narrativeCoherence: 0.55,
    thresholds: defaultPolicyThresholds(),
    scores: [
      { name: "resonance", value: 0.52, weight: 0.5, explanation: "adjusted resonance 0.520" },
      { name: "divergence", value: 0.85, weight: 0.2, explanation: "divergence drifting" },
      { name: "narrative", value: 0.4, weight: 0.1, explanation: "narrative weak" },
      { name: "effect_risk", value: 0.7, weight: 0.2, explanation: "effect risk moderate" },
    ],
    explanation:
      "aggregate=0.520; resonance=0.520, divergence=0.850, narrative=0.400, effect_risk=0.700",
    modelName: "rule_based",
    modelVersion: "1",
    timestamp: new Date("2024-07-20T15:30:00.000Z"),
  };
}

/**
 * MCP `decide` tool — decision half of the response (`policy_decision_to_dict` / Python
 * `vermyth.mcp.tools._serializers.policy_decision_to_dict`).
 */
describe("policyDecisionToDict golden parity", () => {
  it("matches committed policy decision fixture (ALLOW, no suggested_intent)", () => {
    const goldenPath = join(__dirname, "fixtures", "policy-decision-golden.json");
    const golden = JSON.parse(readFileSync(goldenPath, "utf8")) as Record<string, unknown>;
    const decision = buildGoldenPolicyDecision();
    expect(policyDecisionToDict(decision)).toEqual(golden);
  });

  it("matches committed policy decision fixture (RESHAPE, non-null suggested_intent)", () => {
    const goldenPath = join(__dirname, "fixtures", "policy-decision-reshape-golden.json");
    const golden = JSON.parse(readFileSync(goldenPath, "utf8")) as Record<string, unknown>;
    const decision = buildGoldenPolicyDecisionReshape();
    expect(policyDecisionToDict(decision)).toEqual(golden);
  });
});
