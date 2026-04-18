/** Arcane semantic bundle catalog — minimal stubs until full `vermyth.arcane` port. */

export function listBundleCatalog(kind?: "decide" | "cast" | "compile_program" | null): Array<Record<string, unknown>> {
  void kind;
  return [];
}

export function inspectSemanticBundleDetail(bundleId: string, version: number): Record<string, unknown> {
  return {
    bundle_id: bundleId,
    version,
    manifest: { stub: true },
    preview: null,
  };
}

/** Telemetry summary stub — Python `get_bundle_adoption_summary`. */
export function getBundleAdoptionSummary(): Record<string, unknown> {
  return {
    listed_total: 0,
    inspected_total: 0,
    by_kind: {},
    stub: true,
  };
}
