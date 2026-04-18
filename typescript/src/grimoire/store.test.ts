import { describe, expect, it } from "vitest";

import { buildTools } from "../bootstrap.js";
import { castAspectNames } from "../engine/operations/casting.js";
import { ReversibilityClass, SideEffectTolerance } from "../schema/enums.js";

describe("Grimoire", () => {
  it("runs migrations and records a cast", () => {
    const { engine, grimoire } = buildTools(":memory:");
    const intent = {
      objective: "persist",
      scope: "memory",
      reversibility: ReversibilityClass.PARTIAL,
      sideEffectTolerance: SideEffectTolerance.NONE,
    };
    const result = castAspectNames(engine, ["LIGHT", "MIND"], intent);
    grimoire.casts.write(result);
    expect(grimoire.migrationCount()).toBeGreaterThan(0);
    grimoire.close();
  });
});
