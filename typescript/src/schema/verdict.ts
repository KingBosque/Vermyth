import type { VerdictType } from "./enums.js";
import type { IntentVector } from "./intent.js";

export interface ResonanceScore {
  raw: number;
  adjusted: number;
  ceilingApplied: boolean;
  proof: string;
}

export interface Verdict {
  verdictType: VerdictType;
  resonance: ResonanceScore;
  effectDescription: string;
  incoherenceReason: string | null;
  castingNote: string;
  intentVector: IntentVector;
}
