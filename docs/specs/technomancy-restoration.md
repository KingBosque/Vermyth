# Technomancy restoration spec

This document is **repo-specific**. It does not replace [ontology.md](ontology.md) or [arcane-design-summary.md](arcane-design-summary.md); it coordinates **decorative**, **semantic**, and **operative** layers so Vermyth can regain a disciplined sense of technomancy **without** weakening stable contracts ([STABILITY.md](../STABILITY.md), JSON goldens, MCP error semantics).

## 1. Decorative / general technomancy

### Purpose

Improve **human and agent-facing feel** (names, framing, optional arcane labels) while keeping **wire truth** boring, explicit, and testable.

### Presentation rules

- **Stable JSON keys** (`cast_id`, `verdict`, `resonance`, etc.) are **not** renamed for flavor in default MCP/HTTP responses.
- **Arcane labels** may appear as **additive** fields (e.g. `arcane_transcript`) or parallel CLI output modes, never as silent rewrites of numeric or enum semantics.
- **Dual rendering:** Any “mundane vs arcane” view must be **derivable from the same underlying result**; if a second view is shown, it must be labeled **presentation-only** where it does not add new computation.

### Naming rules

- **Stable surface** tool and field names stay aligned with [STABILITY.md](../STABILITY.md) and cross-language goldens (TypeScript parity tests).
- **Prose** (casting notes, effect descriptions) may use arcane vocabulary; **schemas** stay technical where interoperability matters.

### What stays boring and explicit

- Pydantic / JSON schemas, migration versions, pytest markers, `VERMYTH_EXPERIMENTAL_TOOLS` gates.
- Error codes and validation messages on MCP/HTTP.
- “NOT_PORTED” / stub responses on the TypeScript edge where parity is not claimed ([typescript/src/arcane/bundles.ts](../../typescript/src/arcane/bundles.ts)).

### What may gain arcane presentation

- CLI output (optional flags), docs, optional additive blobs on responses **after** opt-in design review.
- **[vermyth.arcane.presentation](../../vermyth/arcane/presentation/transcript.py)** `arcane_transcript_for_cast_result`: deterministic, inspectable labels derived only from existing `CastResult` fields (see section 3).

---

## 2. Semantic / atomized technomancy

Canonical atoms below extend [ontology.md](ontology.md). For each: **meaning**, **tier**, **layer**, **compiles into**, **evidence**, **loss if removed**, **status** (real / partial / decorative).

| Atom | Meaning (short) | Stable / experimental | Layer | Compiles into | Evidence it fired | Loss if removed | Status |
|------|-----------------|-------------------------|-------|---------------|-------------------|-----------------|--------|
| **Aspect** | Basis dimension for vectors | Stable | Schema + registry + persistence | `SemanticVector` components, composition keys | Sigil vector, basis version | No geometry | **Real** |
| **Sigil** | Composed 1–3 aspect symbol | Stable | Schema + `CompositionEngine` | Named sigil, effect class, ceiling, contradiction | `CastResult.sigil` | No evaluation target | **Real** |
| **Intent** | Declared situation | Stable | Schema | Constraint / semantic vectors | `CastResult.intent` | No alignment story | **Real** |
| **Resonance** | Cosine-based alignment + ceiling | Stable | Runtime | `Verdict.resonance.adjusted` | Numeric proof string | No decision signal | **Real** |
| **Verdict** | COHERENT / PARTIAL / INCOHERENT bands | Stable | Runtime | Policy inputs | Verdict enum | No banding | **Real** |
| **Divergence** | Parent/child drift | Stable | Policy + grimoire | `DivergenceStatus`, policy scorer | Lineage + reports when configured | Weaker drift policy | **Real** |
| **Grimoire** | Durable history | Stable | Persistence | SQLite rows | `cast_id`, queries | No audit trail | **Real** |
| **Ritual** | Named workflow → program | Stable (Python) | Arcane compiler | `SemanticProgram` + metadata | Compile receipts | Lose named DAG templates | **Real** (Python); TS not full parity |
| **Ward** | Threshold overlay | Stable (Python) | Arcane compiler | Merged `PolicyThresholds` | stricter ALLOW region when applied | Default thresholds only | **Real** (Python) |
| **Divination** | Causal / review gate | Stable (Python) | Arcane + policy | Requires `causal_root` or thresholds | explicit failures / merges | Manual causal discipline | **Real** (Python) |
| **Banishment** | Containment / rollback rules | Stable (Python) | Arcane compile | Rollback validation | validation warnings/errors | Generic rollback only | **Real** (Python) |
| **Genesis / Swarm** | Emergent aspects / peer aggregation | **Experimental** | Engine + MCP (gated) | Swarm vectors, genesis flows | gated tools | Research-only paths | **Partial / experimental** |

**Decorative-only (explicit):** `EffectClass` for **casting note** selection does not change resonance math ([ontology.md](ontology.md) “Presentation-only”).

---

## 3. Operative technomancy

Operative technomancy means **actions leave inspectable artifacts** tied to real computation—not theater without traces.

### Phases (mapping to existing runtime)

| Phase | Arcane label | Maps to (mundane) | User/agent-visible manifestation | Receipts / traces |
|-------|--------------|-------------------|-----------------------------------|-------------------|
| Attunement | Constraint of will | `Intent` + `IntentVector` construction | Objective, scope, tolerance; projection method | Intent fields on `CastResult` |
| Warding | Boundary / threshold | Ward merge from **bundles** / `PolicyThresholds` | Stricter ALLOW region when wards applied | Merged thresholds on `decide`; N/A for plain `cast` without bundle |
| Casting | Invocation | `CompositionEngine` + resonance | Sigil name, aspects, verdict, resonance | Full `CastResult` |
| Divination / verification | Read of alignment | Verdict + optional causal / narrative policy inputs | Verdict type, narrative coherence when used | `Verdict`, causal subgraph when queried |
| Stabilization / banishment | Containment | Policy DENY / rollback validation | Policy action, program validation | PolicyDecision; program compile warnings |
| Residue | What remains | Persistence + lineage | `cast_id`, timestamp, `lineage`, provenance | Grimoire rows, optional `arcane_provenance` on bundle paths |

**Honesty rule:** Phases without inputs (e.g. warding on a raw cast with no bundle) must be **omitted** or marked **not_applicable**—see `arcane_transcript_for_cast_result`.

### Additive presentation: `arcane_transcript`

Module: [vermyth/arcane/presentation/transcript.py](../../vermyth/arcane/presentation/transcript.py).

- **Does not** change scores, thresholds, or MCP defaults.
- **Does** expose a structured, deterministic summary of which **mundane anchors** exist on a `CastResult` under arcane phase names.
- Marked **`presentation_only: true`** in output.

### Opt-in surfaces (CLI / MCP)

- **MCP:** `cast`, `fluid_cast`, and `auto_cast` accept optional **`include_arcane_transcript`** (boolean). When `true`, the tool response includes an additive **`arcane_transcript`** field (same structure as `arcane_transcript_for_cast_result`). Omitted or `false` preserves the default wire shape (no `arcane_transcript` key).
- **CLI:** `cast`, `fluid-cast`, and `auto-cast` accept **`--arcane-transcript`**. After the usual human-readable cast summary, the CLI prints a labeled block with JSON for the transcript. Default runs are unchanged.

---

## 4. Experimental reintegration findings

| Surface | Current status | Technomantic / runtime value | Recommendation |
|---------|----------------|------------------------------|----------------|
| Session codec V2, `vermyth.protocol.session_codec` | Experimental | Replay-safe transport research | **Preserve experimental** — high churn; do not merge to stable contract without a product driver |
| Swarm / gossip MCP tools | Gated (`VERMYTH_EXPERIMENTAL_TOOLS`) | Peer aggregation; TS stubbed / `NOT_PORTED` | **Preserve experimental**; reintegrate only with security review + TS parity plan |
| Genesis MCP | Experimental but reviewed | Emergent aspects | **Fold only after** dedicated tests + STABILITY promotion |
| Geometric / binary MCP | Experimental | Wire helpers (lossy where documented) | **Preserve experimental** untilinterop story is clear |
| A2A optional server | Optional extra `[a2a]` | Agent interop | **Keep optional** — orthogonal to core technomancy feel |
| Arcane bundles (Python) | **Stable** | Compiler + manifests under `vermyth/data/arcane/bundles/` | **Already main** — restore *feel* by surfacing bundles on TS (read-only catalog) rather than merging unrelated experimental code |

**Merge-back rules (summary):** Require tests, STABILITY update, no silent drift of stable defaults, and honest stubs where TypeScript is not yet parity.

---

## 5. TypeScript / Python hybrid

- Python remains the **oracle** for proven JSON wire shapes (see [typescript/README.md](../../typescript/README.md)).
- TypeScript **must not** claim arcane bundle parity while [typescript/src/arcane/bundles.ts](../../typescript/src/arcane/bundles.ts) returns empty/stub catalog.
- Restoration work on the Node edge should prefer **synced read-only bundle metadata** or explicit “not ported” over fake richness.

---

## 6. Decision rules (reintegration and presentation)

1. **No merge** of experimental code **solely** for atmosphere.
2. **Promote** to stable only with tests, docs, and STABILITY.md entry.
3. **Presentation** layers must declare **`presentation_only`** when they do not add computation.
4. **Stubbed** surfaces stay **explicit** (`NOT_PORTED`, empty catalog) until implemented.
5. **Goldens** and stable tool names take precedence over renaming for lore.

---

## 7. Verification

After changing this spec or presentation modules:

```bash
pytest tests/test_arcane_transcript.py tests/test_arcane_transcript_exposure.py
pytest tests/ -q --ignore=tests/test_swarm_evolution.py  # example; run full suite in CI
```

TypeScript (if arcane/TS touched):

```bash
cd typescript && npm ci && npm run lint && npm run build && npm test
```

---

## 8. Next stop / go

- **Done (narrow slice):** Opt-in `arcane_transcript` on MCP `cast` / `fluid_cast` / `auto_cast` and CLI `--arcane-transcript` on matching commands.
- **Go:** TS arcane catalog from synced `vermyth/data/arcane/bundles` read-only.
- **Pause:** Merging swarm/session experimental lines without bounded scope.
