import { AspectRegistry } from "../registry.js";

export interface ProjectionBackend {
  project(objective: string, scope: string): number[];
}

function clip(x: number): number {
  return Math.max(-1, Math.min(1, x));
}

function normalize(components: readonly number[]): number[] {
  let s = 0;
  for (const c of components) {
    s += c * c;
  }
  const norm = Math.sqrt(s);
  if (norm === 0) {
    return components.map(() => 0);
  }
  return components.map((c) => c / norm);
}

function safeStderr(message: string): void {
  try {
    process.stderr.write(`${message}\n`);
  } catch {
    /* ignore */
  }
}

const ASPECT_KEYWORDS: Record<string, readonly string[]> = {
  VOID: ["delete", "remove", "erase", "null", "empty", "void", "silence"],
  FORM: ["shape", "structure", "format", "schema", "organize", "compose", "build"],
  MOTION: ["move", "flow", "shift", "change", "migrate", "iterate", "progress"],
  MIND: ["think", "understand", "analyze", "reason", "learn", "explain", "decide"],
  DECAY: ["decay", "break", "corrupt", "rot", "deprecate", "fade", "entropy"],
  LIGHT: ["reveal", "clarify", "expose", "illuminate", "shine", "discover", "signal"],
};

export class NullProjectionBackend implements ProjectionBackend {
  project(_objective: string, _scope: string): number[] {
    return [];
  }
}

export class LocalProjectionBackend implements ProjectionBackend {
  project(objective: string, scope: string): number[] {
    const text = `${objective}\n${scope}`.toLowerCase();
    const dim = AspectRegistry.get().dimensionality;
    const base: number[] = Array(Math.max(6, dim)).fill(0);
    const canonical = ["VOID", "FORM", "MOTION", "MIND", "DECAY", "LIGHT"] as const;
    for (let i = 0; i < canonical.length; i++) {
      const name = canonical[i]!;
      const kws = ASPECT_KEYWORDS[name] ?? [];
      let hits = 0;
      for (const kw of kws) {
        if (text.includes(kw)) {
          hits += 1;
        }
      }
      if (hits) {
        base[i] = clip(0.25 * hits);
      }
    }
    let norm = normalize(base);
    if (dim > norm.length) {
      norm = norm.concat(Array(dim - norm.length).fill(0));
    }
    return norm.slice(0, dim);
  }
}

export class FallbackProjectionBackend implements ProjectionBackend {
  constructor(
    private readonly primary: ProjectionBackend,
    private readonly fallback: ProjectionBackend,
  ) {}

  project(objective: string, scope: string): number[] {
    try {
      const out = this.primary.project(objective, scope);
      if (!Array.isArray(out) || out.length < 6) {
        throw new Error("primary backend returned invalid vector");
      }
      return out;
    } catch (exc) {
      safeStderr(`[vermyth] projection backend primary failed: ${String(exc)}`);
      return this.fallback.project(objective, scope);
    }
  }
}

/**
 * Mirrors `vermyth.engine.projection_backends.backend_from_env`.
 * Modes: none | local | llm | auto (embed omitted — use Python or add sentence-transformers later).
 */
export function backendFromEnv(): ProjectionBackend {
  const mode = (process.env.VERMYTH_BACKEND ?? "none").trim().toLowerCase();
  const fallbackMode = (process.env.VERMYTH_FALLBACK ?? "local").trim().toLowerCase();

  if (!["none", "local", "llm", "auto"].includes(mode)) {
    throw new Error("VERMYTH_BACKEND must be one of: none, local, llm, auto");
  }
  if (!["local", "none"].includes(fallbackMode)) {
    throw new Error("VERMYTH_FALLBACK must be one of: local, none");
  }

  if (mode === "none") {
    return new NullProjectionBackend();
  }
  if (mode === "local") {
    return new LocalProjectionBackend();
  }

  const apiKey = (
    process.env.VERMYTH_ANTHROPIC_API_KEY ?? process.env.VERMYTH_API_KEY ??
    ""
  ).trim();
  if (!apiKey) {
    if (mode === "llm") {
      throw new Error("Missing API key for LLM backend");
    }
    const fallback =
      fallbackMode === "local" ? new LocalProjectionBackend() : new NullProjectionBackend();
    return fallback;
  }

  // LLM path without bundling anthropic: fall back like auto without key
  safeStderr("[vermyth-ts] LLM projection requires runtime integration; falling back.");
  const fallback =
    fallbackMode === "local" ? new LocalProjectionBackend() : new NullProjectionBackend();
  if (mode === "llm") {
    return fallback;
  }
  return new FallbackProjectionBackend(new NullProjectionBackend(), fallback);
}
