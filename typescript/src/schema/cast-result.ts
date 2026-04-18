import { ulid } from "ulidx";

import type { Intent } from "./intent.js";
import type { Verdict } from "./verdict.js";
import type { FluidSigil, Sigil } from "./sigil.js";
import type { CastProvenance } from "./cast-provenance.js";
import type { Lineage } from "./lineage.js";

export interface CastResult {
  castId: string;
  timestamp: Date;
  intent: Intent;
  sigil: Sigil | FluidSigil;
  verdict: Verdict;
  immutable: boolean;
  lineage?: Lineage | null;
  glyphSeedId?: string | null;
  provenance?: CastProvenance | null;
}

export function createCastResult(params: {
  intent: Intent;
  sigil: Sigil | FluidSigil;
  verdict: Verdict;
  lineage?: Lineage | null;
  glyphSeedId?: string | null;
  provenance?: CastProvenance | null;
  castId?: string;
  timestamp?: Date;
}): CastResult {
  return {
    castId: params.castId ?? ulid(),
    timestamp: params.timestamp ?? new Date(),
    intent: params.intent,
    sigil: params.sigil,
    verdict: params.verdict,
    immutable: true,
    lineage: params.lineage,
    glyphSeedId: params.glyphSeedId,
    provenance: params.provenance,
  };
}

export function castResultWithLineage(
  base: CastResult,
  lineage: Lineage,
  provenance?: CastProvenance | null,
): CastResult {
  return {
    ...base,
    lineage,
    provenance: provenance ?? base.provenance,
  };
}
