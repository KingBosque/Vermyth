import { CompositionEngine } from "./engine/composition.js";
import {
  NullProjectionBackend,
  backendFromEnv,
  type ProjectionBackend,
} from "./engine/projection.js";
import { ResonanceEngine } from "./engine/resonance.js";
import { Grimoire } from "./grimoire/store.js";
import { AspectRegistry } from "./registry.js";
import { aspectName } from "./schema/aspect.js";
import type { Aspect } from "./schema/aspect.js";
import { VermythTools } from "./mcp/tools/facade.js";
import { EventBus } from "./observability/event-bus.js";

export function buildTools(
  dbPath?: string | null,
  opts?: { backend?: ProjectionBackend | null },
): {
  grimoire: Grimoire;
  composition: CompositionEngine;
  engine: ResonanceEngine;
  tools: VermythTools;
} {
  const grimoire = new Grimoire(dbPath ?? undefined);
  const registry = AspectRegistry.get();
  const latest = grimoire.readLatestBasisVersion();

  for (const [aspect] of grimoire.queryRegisteredAspects()) {
    if (!registry.isRegistered(aspect.name)) {
      registry.register(aspect);
    }
  }
  registry.setBasisVersion(latest.version);

  const composition = new CompositionEngine();
  for (const row of grimoire.queryRegisteredSigils()) {
    const aspects = new Set<Aspect>();
    for (const n of row.aspects) {
      aspects.add(registry.resolve(n));
    }
    composition.registerSigilEntry(
      aspects,
      {
        name: row.name,
        aspects: [...aspects].map((a) => aspectName(a)),
        effect_class: row.effect_class,
        resonance_ceiling: row.resonance_ceiling,
        contradiction_severity: row.contradiction_severity,
      },
      { allowOverride: row.is_override },
    );
  }

  const engine = new ResonanceEngine(
    composition,
    opts?.backend ?? new NullProjectionBackend(),
    composition.contradictionsMap,
  );
  const tools = new VermythTools(engine, grimoire, new EventBus());
  return { grimoire, composition, engine, tools };
}

export function buildToolsFromEnv(dbPath?: string | null): {
  grimoire: Grimoire;
  composition: CompositionEngine;
  engine: ResonanceEngine;
  tools: VermythTools;
} {
  return buildTools(dbPath, { backend: backendFromEnv() });
}
