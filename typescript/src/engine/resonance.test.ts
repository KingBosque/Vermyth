import { describe, expect, it } from "vitest";

import { CompositionEngine } from "./composition.js";
import { NullProjectionBackend } from "./projection.js";
import { ResonanceEngine } from "./resonance.js";
import { ReversibilityClass, SideEffectTolerance } from "../schema/enums.js";
import { castAspectNames } from "./operations/casting.js";

describe("ResonanceEngine", () => {
  it("evaluates cast end-to-end", () => {
    const composition = new CompositionEngine();
    const engine = new ResonanceEngine(composition, new NullProjectionBackend(), composition.contradictionsMap);
    const intent = {
      objective: "test objective",
      scope: "test scope",
      reversibility: ReversibilityClass.REVERSIBLE,
      sideEffectTolerance: SideEffectTolerance.LOW,
    };
    const result = castAspectNames(engine, ["VOID", "FORM"], intent);
    expect(result.verdict.verdictType).toBeDefined();
    expect(result.castId).toBeDefined();
  });
});
