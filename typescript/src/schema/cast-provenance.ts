export type CastProvenanceSource = "base" | "crystallized" | "fluid";

export interface CastProvenance {
  source: CastProvenanceSource;
  crystallizedSigilName?: string | null;
  generation?: number | null;
  narrativeCoherence?: number | null;
  causalRootCastId?: string | null;
}
