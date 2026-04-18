import { AspectRegistry } from "../../registry.js";
import type { Intent, IntentVector } from "../../schema/intent.js";
import { createIntentVector } from "../../schema/intent.js";
import type { ProjectionMethod, ReversibilityClass, SideEffectTolerance } from "../../schema/enums.js";
import { ProjectionMethod as PM } from "../../schema/enums.js";
import type { SemanticVector } from "../../schema/vectors.js";
import { createSemanticVector } from "../../schema/vectors.js";
import type { ProjectionBackend } from "../projection.js";

const REVERSIBILITY_PRESSURES: Record<ReversibilityClass, readonly number[]> = {
  IRREVERSIBLE: [0.8, -0.4, 0, 0, 0.7, -0.3],
  PARTIAL: [0, 0, 0.3, 0.2, 0, 0],
  REVERSIBLE: [-0.5, 0.7, 0, 0, -0.4, 0.6],
};

const SIDE_EFFECT_PRESSURES: Record<SideEffectTolerance, readonly number[]> = {
  NONE: [-0.6, 0.6, 0, 0, -0.5, 0.5],
  LOW: [-0.2, 0.3, 0, 0.3, -0.2, 0],
  MEDIUM: [0, 0, 0.2, 0.2, 0, 0],
  HIGH: [0.4, -0.3, 0.3, 0, 0.5, 0],
};

export interface IntentEngineLike {
  backend: ProjectionBackend | null;
  clipComponent(x: number): number;
  normalizeUnit(components: readonly number[]): SemanticVector;
}

function logStderr(message: string): void {
  try {
    process.stderr.write(`${message}\n`);
  } catch {
    /* ignore */
  }
}

export function clipComponent(x: number): number {
  if (x > 1) {
    return 1;
  }
  if (x < -1) {
    return -1;
  }
  return x;
}

export function normalizeUnit(components: readonly number[]): SemanticVector {
  const basisVersion = AspectRegistry.get().getBasisVersion();
  const s = components.reduce((acc, c) => acc + c * c, 0);
  const norm = Math.sqrt(s);
  if (norm === 0) {
    return createSemanticVector(components.map(() => 0), basisVersion);
  }
  return createSemanticVector(
    components.map((c) => c / norm),
    basisVersion,
  );
}

export function buildConstraintVector(engine: IntentEngineLike, intent: Intent): SemanticVector {
  const dim = AspectRegistry.get().dimensionality;
  const acc = Array(dim).fill(0) as number[];
  const rev6 = REVERSIBILITY_PRESSURES[intent.reversibility];
  const side6 = SIDE_EFFECT_PRESSURES[intent.sideEffectTolerance];
  const rev = [...rev6, ...Array(Math.max(0, dim - rev6.length)).fill(0)];
  const side = [...side6, ...Array(Math.max(0, dim - side6.length)).fill(0)];
  for (let i = 0; i < dim; i++) {
    acc[i] = engine.clipComponent((rev[i] ?? 0) + (side[i] ?? 0));
  }
  return engine.normalizeUnit(acc);
}

export function buildSemanticVector(
  engine: IntentEngineLike,
  intent: Intent,
): SemanticVector | null {
  if (engine.backend === null) {
    return null;
  }
  try {
    const rawList = engine.backend.project(intent.objective, intent.scope);
    if (!Array.isArray(rawList) || rawList.length < 6) {
      logStderr("[vermyth] projection backend failed: invalid list length");
      return null;
    }
    const floats: number[] = [];
    for (const x of rawList) {
      if (typeof x !== "number" || Number.isNaN(x)) {
        logStderr("[vermyth] projection backend failed: non-numeric component");
        return null;
      }
      const xf = Number(x);
      if (xf < -1 || xf > 1) {
        logStderr("[vermyth] projection backend failed: component out of range");
        return null;
      }
      floats.push(xf);
    }
    const dim = AspectRegistry.get().dimensionality;
    while (floats.length < dim) {
      floats.push(0);
    }
    const s = floats.reduce((a, f) => a + f * f, 0);
    const norm = Math.sqrt(s);
    if (norm === 0) {
      return createSemanticVector(
        floats.map(() => 0),
        AspectRegistry.get().getBasisVersion(),
      );
    }
    return createSemanticVector(
      floats.map((f) => f / norm),
      AspectRegistry.get().getBasisVersion(),
    );
  } catch (exc) {
    logStderr(`[vermyth] projection backend failed: ${String(exc)}`);
    return null;
  }
}

export function combineVectors(
  _engine: IntentEngineLike,
  constraint: SemanticVector,
  semantic: SemanticVector | null,
): { combined: SemanticVector; method: ProjectionMethod; confidence: number } {
  if (semantic === null) {
    return { combined: constraint, method: PM.PARTIAL, confidence: 0.6 };
  }
  const dim = constraint.components.length;
  const combined: number[] = [];
  for (let i = 0; i < dim; i++) {
    const s = i < semantic.components.length ? semantic.components[i]! : 0;
    combined.push(constraint.components[i]! * 0.35 + s * 0.65);
  }
  const combinedT = combined;
  const s = combinedT.reduce((a, c) => a + c * c, 0);
  const norm = Math.sqrt(s);
  if (norm === 0) {
    return { combined: constraint, method: PM.PARTIAL, confidence: 0.6 };
  }
  const t = combinedT.map((c) => c / norm);
  return {
    combined: createSemanticVector(t, AspectRegistry.get().getBasisVersion()),
    method: PM.FULL,
    confidence: 1,
  };
}

export function buildIntentVector(engine: IntentEngineLike, intent: Intent): IntentVector {
  const constraint = buildConstraintVector(engine, intent);
  const semantic = buildSemanticVector(engine, intent);
  const { combined, method, confidence } = combineVectors(engine, constraint, semantic);
  return createIntentVector({
    vector: combined,
    projectionMethod: method,
    constraintComponent: constraint,
    semanticComponent: semantic,
    confidence,
  });
}

export function alignmentWord(cosine: number): string {
  if (cosine >= 0.7) {
    return "strongly";
  }
  if (cosine >= 0.4) {
    return "moderately";
  }
  if (cosine >= 0.1) {
    return "weakly";
  }
  return "opposingly";
}

export function penaltyPhrase(severity: import("../../schema/enums.js").ContradictionSeverity): string {
  if (severity === "HARD") {
    return "HARD contradiction penalised -0.40";
  }
  if (severity === "SOFT") {
    return "SOFT contradiction penalised -0.18";
  }
  return "no contradiction penalty";
}
