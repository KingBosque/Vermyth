import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { sigilsDir } from "../paths.js";
import type { Aspect } from "../schema/aspect.js";
import { aspectIdFromName } from "../schema/aspect.js";
import type { EffectClass } from "../schema/enums.js";
import { ContradictionSeverity as CS, EffectClass as EC } from "../schema/enums.js";
import {
  buildFluidSigil,
  buildSigil,
  fluidPolarityFromVector,
  normalizeSemanticVectorForComposition,
} from "../schema/sigil.js";
import type { SemanticVector } from "../schema/vectors.js";
import { cosineSimilarity, semanticVectorFromAspects } from "../schema/vectors.js";
import { canonicalAspectKey } from "./keys.js";

function parseEffectClass(raw: unknown): EffectClass {
  const s = String(raw);
  if (s in EC) {
    return EC[s as keyof typeof EC];
  }
  throw new Error(`unknown effect_class: ${JSON.stringify(raw)}`);
}

type SigilTableEntry = {
  name: string;
  aspects: string[];
  effect_class: string;
  resonance_ceiling: number;
  contradiction_severity?: string;
};

export class CompositionEngine {
  private readonly dataDir: string;
  private readonly table: Map<string, Record<string, unknown>> = new Map();
  private contradictions: Record<string, Record<string, unknown>> = {};

  constructor(
    dataDir?: string,
    contradictions?: Record<string, Record<string, unknown>> | null,
  ) {
    this.dataDir = dataDir ?? sigilsDir();
    this.loadTable();
    if (contradictions === undefined || contradictions === null) {
      this.loadContradictions();
    } else {
      this.contradictions = contradictions;
    }
  }

  get contradictionsMap(): Record<string, Record<string, unknown>> {
    return this.contradictions;
  }

  private loadContradictions(): void {
    const path = join(this.dataDir, "contradictions.json");
    try {
      const raw = readFileSync(path, "utf8");
      const loaded = JSON.parse(raw) as unknown;
      if (loaded && typeof loaded === "object" && !Array.isArray(loaded)) {
        this.contradictions = loaded as Record<string, Record<string, unknown>>;
      } else {
        this.contradictions = {};
      }
    } catch {
      this.contradictions = {};
    }
  }

  private ingestSigilFile(path: string): void {
    const entries = JSON.parse(readFileSync(path, "utf8")) as unknown;
    if (!Array.isArray(entries)) {
      throw new Error(`expected JSON array in ${path}`);
    }
    for (const entry of entries) {
      if (!entry || typeof entry !== "object") {
        throw new Error(`invalid entry in ${path}`);
      }
      const e = entry as SigilTableEntry;
      const rawNames = e.aspects;
      if (!Array.isArray(rawNames)) {
        throw new Error(`entry missing aspects array in ${path}`);
      }
      const aspectSet = new Set<Aspect>();
      for (const name of rawNames) {
        if (typeof name !== "string") {
          throw new Error(`invalid aspect name in ${path}`);
        }
        aspectSet.add(aspectIdFromName(name));
      }
      const aspectsFs = aspectSet;
      const key = canonicalAspectKey(aspectsFs);
      if (this.table.has(key)) {
        throw new Error(`duplicate canonical sigil key: ${JSON.stringify(key)}`);
      }
      this.table.set(key, entry as Record<string, unknown>);
    }
  }

  private loadTable(): void {
    const dir = this.dataDir;
    for (const name of readdirSync(dir).sort()) {
      if (!name.endsWith(".json")) {
        continue;
      }
      if (name === "contradictions.json") {
        continue;
      }
      this.ingestSigilFile(join(dir, name));
    }
    const extended = join(dir, "extended");
    try {
      if (statSync(extended).isDirectory()) {
        for (const name of readdirSync(extended).sort()) {
          if (name.endsWith(".json")) {
            this.ingestSigilFile(join(extended, name));
          }
        }
      }
    } catch {
      /* optional */
    }
  }

  private contradictionSeverityForKey(key: string, raw: Record<string, unknown>): CS {
    const sevOverride = raw["contradiction_severity"];
    if (sevOverride === "NONE" || sevOverride === "SOFT" || sevOverride === "HARD") {
      return sevOverride;
    }
    const contra = this.contradictions[key];
    if (!contra) {
      return CS.NONE;
    }
    const sev = contra["severity"];
    if (sev === "NONE" || sev === "SOFT" || sev === "HARD") {
      return sev;
    }
    return CS.NONE;
  }

  compose(aspects: ReadonlySet<Aspect>): ReturnType<typeof buildSigil> {
    const n = aspects.size;
    if (n < 1) {
      throw new Error("aspects must contain at least one AspectID");
    }
    if (n > 3) {
      throw new Error("aspects must contain at most three AspectIDs");
    }
    const key = canonicalAspectKey(aspects);
    const raw = this.table.get(key);
    if (!raw) {
      throw new Error(`no defined resolution for aspect combination: ${JSON.stringify(key)}`);
    }
    const contradictionSeverity = this.contradictionSeverityForKey(key, raw);
    const name = String(raw["name"]);
    const effectClass = parseEffectClass(raw["effect_class"]);
    const resonanceCeiling = Number(raw["resonance_ceiling"]);
    return buildSigil({
      name,
      aspects,
      effectClass,
      resonanceCeiling,
      contradictionSeverity,
    });
  }

  interpolate(vector: SemanticVector, k = 3): ReturnType<typeof buildFluidSigil> {
    if (k < 1) {
      throw new Error("k must be >= 1");
    }
    const vec = normalizeSemanticVectorForComposition(vector);
    const scored: Array<{
      sim: number;
      key: string;
      raw: Record<string, unknown>;
      aspects: ReadonlySet<Aspect>;
    }> = [];

    for (const [key, raw] of this.table) {
      const rawNames = raw["aspects"];
      if (!Array.isArray(rawNames)) {
        continue;
      }
      const aspectsSet = new Set<Aspect>();
      let ok = true;
      for (const name of rawNames) {
        if (typeof name !== "string") {
          ok = false;
          break;
        }
        try {
          aspectsSet.add(aspectIdFromName(name));
        } catch {
          ok = false;
          break;
        }
      }
      if (!ok || aspectsSet.size === 0) {
        continue;
      }
      const aspectsFs = aspectsSet;
      const anchorVec = semanticVectorFromAspects(aspectsFs);
      const sim = cosineSimilarity(anchorVec, vec);
      scored.push({ sim, key, raw, aspects: aspectsFs });
    }

    if (scored.length === 0) {
      throw new Error("no sigil anchors available for interpolation");
    }

    scored.sort((a, b) => b.sim - a.sim);
    const neighbors = scored.slice(0, Math.min(k, scored.length));

    const sims = neighbors.map((n) => n.sim);
    const maxSim = Math.max(...sims);
    const exps = sims.map((s) => Math.exp(s - maxSim));
    const denom = exps.reduce((a, b) => a + b, 0) || 1;
    const weights = exps.map((e) => e / denom);

    const weightByName: Record<string, number> = {};
    const unionAspects = new Set<Aspect>();
    let resonanceCeiling = 0;
    let worstSeverity: CS = CS.NONE;

    const severityRank: Record<CS, number> = {
      [CS.NONE]: 0,
      [CS.SOFT]: 1,
      [CS.HARD]: 2,
    };

    let bestIdx = 0;
    for (let i = 1; i < neighbors.length; i++) {
      if (weights[i]! > weights[bestIdx]!) {
        bestIdx = i;
      }
    }
    const bestRaw = neighbors[bestIdx]!.raw;
    const bestAspects = neighbors[bestIdx]!.aspects;
    const bestName = String(bestRaw["name"] ?? "UNKNOWN");
    const bestEffectClass = parseEffectClass(bestRaw["effect_class"]);

    for (let i = 0; i < neighbors.length; i++) {
      const w = weights[i]!;
      const { key, raw, aspects: aspectsFs } = neighbors[i]!;
      const name = String(raw["name"] ?? key);
      weightByName[name] = (weightByName[name] ?? 0) + w;
      for (const a of aspectsFs) {
        unionAspects.add(a);
      }
      resonanceCeiling += Number(raw["resonance_ceiling"]) * w;
      if (w > 0.1) {
        const sev = this.contradictionSeverityForKey(key, raw);
        if (severityRank[sev] > severityRank[worstSeverity]) {
          worstSeverity = sev;
        }
      }
    }

    let union = unionAspects;
    if (union.size > 3) {
      union = new Set(bestAspects);
    }

    const polarity = fluidPolarityFromVector(vec);
    const nearestCanonical = bestName;
    const fluidName = `Fluid:${nearestCanonical}`;

    const fpBasis =
      [...union]
        .map((a) => a.name)
        .sort()
        .join("+") +
      "|" +
      [...vec.components.slice(0, 6)].map((x) => `${Number(x).toFixed(6)}`).join(",");
    const fp = createHash("sha256").update(JSON.stringify(fpBasis), "utf8").digest("hex");

    return buildFluidSigil({
      name: fluidName,
      aspects: union,
      effectClass: bestEffectClass,
      resonanceCeiling,
      contradictionSeverity: worstSeverity,
      semanticFingerprint: fp,
      semanticVector: vec,
      polarity,
      sourceVector: vector,
      nearestCanonical,
      interpolationWeights: weightByName,
    });
  }

  registerSigilEntry(
    aspects: ReadonlySet<Aspect>,
    entry: Record<string, unknown>,
    opts?: { allowOverride?: boolean },
  ): void {
    const key = canonicalAspectKey(aspects);
    if (this.table.has(key) && !opts?.allowOverride) {
      throw new Error(
        `sigil for aspect combination ${JSON.stringify(key)} already exists; set allowOverride to replace`,
      );
    }
    this.table.set(key, entry);
  }
}
