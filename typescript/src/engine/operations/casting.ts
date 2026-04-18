import { ulid } from "ulidx";

import type { Aspect } from "../../schema/aspect.js";
import { aspectIdFromName } from "../../schema/aspect.js";
import type { Intent } from "../../schema/intent.js";
import type { SemanticVector } from "../../schema/vectors.js";
import { createSemanticVector } from "../../schema/vectors.js";
import type { FluidSigil, Sigil } from "../../schema/sigil.js";
import type { CastResult } from "../../schema/cast-result.js";
import { castResultWithLineage, createCastResult } from "../../schema/cast-result.js";
import type { CastProvenance } from "../../schema/cast-provenance.js";
import type { Lineage } from "../../schema/lineage.js";
import { VerdictType as VT } from "../../schema/enums.js";
import type { ResonanceEngine } from "../resonance.js";
import * as castOps from "./cast-ops.js";

export interface AutoCastDiagnostics {
  steps: Array<{ adjusted: number; raw: number; blend_alpha: number }>;
  converged: boolean;
  finalAdjusted: number;
}

export function cast(
  engine: ResonanceEngine,
  aspects: ReadonlySet<Aspect>,
  intent: Intent,
): CastResult {
  const sigil = engine.compositionEngine.compose(aspects) as Sigil;
  const verdict = engine.evaluate(sigil, intent);
  return createCastResult({ intent, sigil, verdict });
}

export function fluidCast(engine: ResonanceEngine, vector: SemanticVector, intent: Intent): CastResult {
  const sigil = engine.compositionEngine.interpolate(vector) as FluidSigil;
  const verdict = engine.evaluate(sigil, intent);
  const provenance: CastProvenance = { source: "fluid" };
  return createCastResult({ intent, sigil, verdict, provenance });
}

export function castAspectNames(
  engine: ResonanceEngine,
  aspectNames: string[],
  intent: Intent,
): CastResult {
  const aspects = new Set<Aspect>();
  for (const n of aspectNames) {
    aspects.add(aspectIdFromName(n));
  }
  return cast(engine, aspects, intent);
}

export function autoCast(
  engine: ResonanceEngine,
  vector: SemanticVector,
  intent: Intent,
  opts?: {
    maxDepth?: number;
    targetResonance?: number;
    blendAlpha?: number;
    withDiagnostics?: boolean;
  },
):
  | [CastResult, CastResult[]]
  | [CastResult, CastResult[], AutoCastDiagnostics] {
  const maxDepth = opts?.maxDepth ?? 5;
  const targetResonance = opts?.targetResonance ?? 0.75;
  const blendAlpha = opts?.blendAlpha ?? 0.35;
  const withDiagnostics = opts?.withDiagnostics ?? false;

  const branchId = ulid();
  const chain: CastResult[] = [];
  const diagnosticsSteps: Array<{ adjusted: number; raw: number; blend_alpha: number }> = [];
  let current = vector;
  let parentCastId: string | null = null;

  for (let i = 0; i < maxDepth; i++) {
    void i;
    const base = fluidCast(engine, current, intent);
    let result: CastResult;
    if (parentCastId !== null) {
      const parentResult = chain[chain.length - 1]!;
      const pc = parentResult.sigil.semanticVector.components;
      const cc = base.sigil.semanticVector.components;
      const dim = Math.max(cc.length, pc.length);
      const diff: number[] = [];
      for (let j = 0; j < dim; j++) {
        diff.push((j < cc.length ? cc[j]! : 0) - (j < pc.length ? pc[j]! : 0));
      }
      const divVec = createSemanticVector(diff);
      const depthLin =
        parentResult.lineage !== undefined && parentResult.lineage !== null
          ? parentResult.lineage.depth + 1
          : 1;
      const lin: Lineage = {
        parentCastId,
        depth: depthLin,
        branchId,
        divergenceVector: divVec,
      };
      const prov: CastProvenance = { source: "fluid" };
      result = castResultWithLineage(base, lin, prov);
    } else {
      result = base;
    }

    chain.push(result);
    const adj = result.verdict.resonance.adjusted;
    diagnosticsSteps.push({
      adjusted: adj,
      raw: result.verdict.resonance.raw,
      blend_alpha: blendAlpha,
    });

    if (result.verdict.verdictType === VT.COHERENT && adj >= targetResonance) {
      if (withDiagnostics) {
        return [
          result,
          chain,
          { steps: diagnosticsSteps, converged: true, finalAdjusted: adj },
        ];
      }
      return [result, chain];
    }

    const fluid = engine.compositionEngine.interpolate(current);
    current = castOps.blendToward(engine, current, fluid.semanticVector, blendAlpha);
    parentCastId = result.castId;
  }

  const final = chain[chain.length - 1]!;
  const finalAdj = final.verdict.resonance.adjusted;
  if (withDiagnostics) {
    return [
      final,
      chain,
      { steps: diagnosticsSteps, converged: false, finalAdjusted: finalAdj },
    ];
  }
  return [final, chain];
}
