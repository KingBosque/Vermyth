import { describe, expect, it } from "vitest";

import { CompositionEngine } from "./composition.js";
import { aspectIdFromName } from "../schema/aspect.js";
import { EffectClass } from "../schema/enums.js";

describe("CompositionEngine", () => {
  it("composes VOID+FORM+MOTION to Phantokinesis", () => {
    const engine = new CompositionEngine();
    const aspects = new Set([
      aspectIdFromName("VOID"),
      aspectIdFromName("FORM"),
      aspectIdFromName("MOTION"),
    ]);
    const sigil = engine.compose(aspects);
    expect(sigil.name).toBe("Phantokinesis");
    expect(sigil.effectClass).toBe(EffectClass.NEGATION);
  });
});
