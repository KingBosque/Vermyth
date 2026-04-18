import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { castResultToDict } from "./cast-result-json.js";
import { createCastResult } from "../schema/cast-result.js";
import { aspectIdFromName } from "../schema/aspect.js";
import { buildSigil } from "../schema/sigil.js";
import {
  ContradictionSeverity,
  EffectClass,
  ProjectionMethod,
  ReversibilityClass,
  SideEffectTolerance,
  VerdictType,
} from "../schema/enums.js";
import { createIntentVector } from "../schema/intent.js";
import { createSemanticVector } from "../schema/vectors.js";
import { AspectRegistry } from "../registry.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Stable JSON snapshot for `castResultToDict` (MCP / Python `cast_result_to_dict` alignment).
 * Regenerate the fixture if serializer rounding or field set changes intentionally.
 */
function buildGoldenCastResult() {
  const aspects = new Set([aspectIdFromName("VOID"), aspectIdFromName("FORM")]);
  const sigil = buildSigil({
    name: "ParityGolden",
    aspects,
    effectClass: EffectClass.NEGATION,
    resonanceCeiling: 0.85,
    contradictionSeverity: ContradictionSeverity.NONE,
  });
  const dim = AspectRegistry.get().dimensionality;
  const z = createSemanticVector(Array(dim).fill(0), null);
  const intentVector = createIntentVector({
    vector: z,
    projectionMethod: ProjectionMethod.PARTIAL,
    constraintComponent: z,
    semanticComponent: null,
    confidence: 0.5,
  });
  const verdict = {
    verdictType: VerdictType.COHERENT,
    resonance: { raw: 0.81234, adjusted: 0.76543, ceilingApplied: false, proof: "parity-proof" },
    effectDescription: "golden effect",
    incoherenceReason: null,
    castingNote: "golden note",
    intentVector,
  };
  return createCastResult({
    castId: "01HZX8Q4K9ABCDEFGHJKMNPQRS",
    timestamp: new Date("2024-06-01T12:34:56.789Z"),
    intent: {
      objective: "golden objective",
      scope: "golden scope",
      reversibility: ReversibilityClass.REVERSIBLE,
      sideEffectTolerance: SideEffectTolerance.LOW,
    },
    sigil,
    verdict,
    lineage: null,
    glyphSeedId: null,
    provenance: null,
  });
}

describe("castResultToDict golden parity", () => {
  it("matches committed MCP cast summary fixture", () => {
    const goldenPath = join(__dirname, "fixtures", "cast-result-golden.json");
    const golden = JSON.parse(readFileSync(goldenPath, "utf8")) as Record<string, unknown>;
    const result = buildGoldenCastResult();
    expect(castResultToDict(result)).toEqual(golden);
  });
});
