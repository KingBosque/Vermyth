# Vermyth arcane ontology (operational specification)

This document defines **computational** semantics for arcane vocabulary. Names marked **presentation-only** do not change numeric scoring.

## Stability tiers

| Tier | Meaning |
|------|--------|
| **Stable** | Core schema + engine; backward compatibility expected. |
| **Experimental** | Genesis, swarm, optional A2A extensions; may change. |

## Core concepts (stable)

### Aspect

- **Meaning:** A basis dimension for semantic vectors (six canonical `AspectID` enums plus optional `RegisteredAspect` after genesis).
- **Kind:** Schema (`AspectID`, `RegisteredAspect`), runtime (`AspectRegistry`), persistence (basis version).
- **Compiles into:** `SemanticVector` components, `Sigil` composition keys, sigil JSON tables under `vermyth/data/sigils/`.
- **Guarantees:** Canonical order; cosine similarity requires matching `basis_version`.
- **If removed:** No resonance, no composition, no casts.

### Sigil

- **Meaning:** Named composed symbol for 1–3 aspects: effect class, resonance ceiling, contradiction severity, semantic vector.
- **Kind:** Schema; runtime via `CompositionEngine`.
- **Compiles into:** `Sigil` model + JSON rows from `canonical_*.json`.
- **Guarantees:** Fingerprint/vector derived from aspects unless extended tables override.
- **If removed:** No structured evaluation target.

### Intent

- **Meaning:** Declared situation: objective, scope, reversibility, side-effect tolerance.
- **Kind:** Schema; drives `IntentVector` construction.
- **Compiles into:** Constraint vector (semantic optional via projection).
- **Guarantees:** Bounded fields; reversibility/side-effect map to pressure tuples in `ResonanceEngine`.
- **If removed:** No intent-aligned scoring.

### Verdict

- **Meaning:** `COHERENT` / `PARTIAL` / `INCOHERENT` from adjusted resonance thresholds.
- **Kind:** Schema + runtime in `vermyth/engine/operations/cast.py`.
- **Compiles into:** Policy decision inputs.
- **Guarantees:** Thresholds 0.75 / 0.45 for verdict bands (see `verdict_type`).

### Resonance

- **Meaning:** Cosine alignment between intent vector and sigil vector, with contradiction penalty and ceiling.
- **Kind:** Runtime (`ResonanceScore`); schema.
- **Compiles into:** `adjusted` float in `[0,1]` used by policy.
- **Guarantees:** Basis mismatch triggers upsampling.
- **If removed:** No core decision signal.

### Divergence

- **Meaning:** Drift between parent and child cast semantic vectors.
- **Kind:** Policy (`DivergenceReport`, `DivergenceThresholds`); scoring.
- **Compiles into:** `DivergenceStatus` → `DivergenceScorer` → policy ALLOW/RESHAPE/DENY.
- **Guarantees:** Threshold ordering on L2 and cosine distance.

### Grimoire

- **Meaning:** SQLite persistence for casts, programs, receipts, divergence, etc.
- **Kind:** Persistence (`vermyth/grimoire/store.py`); not a protocol type.
- **Compiles into:** Tables and repositories.
- **If removed:** No durable history.

## Arcane layer concepts (stable where implemented in `vermyth/arcane/`)

### Ritual

- **Meaning:** A named semantic **workflow** with optional arcane metadata; **first-class** as `RitualSpec` compiling to `SemanticProgram` with `metadata["arcane"]` and `metadata["ritual"]`.
- **Kind:** Schema (`vermyth/arcane/types.py`); execution + validation.
- **Compiles into:** `SemanticProgram` (DAG of `CastNode`s) + validation; same execution as programs with provenance.
- **Guarantees:** Invalid graphs fail `compile_program`; optional `VERMYTH_DENY_PROGRAM_VALIDATION_WARNINGS`.
- **If removed:** Use raw `SemanticProgram` only; lose named ritual templates and bundle linkage.

### Ward

- **Meaning:** Policy **constraint overlay** (thresholds, drift ceiling, effect-risk gate) optionally scoped to a capability pattern.
- **Kind:** Schema `WardSpec`; policy + compile.
- **Compiles into:** `PolicyThresholds` merge (see `vermyth/arcane/compiler.py`) applied to `decide` / bundle expansion.
- **Guarantees:** Stricter wards monotonically shrink ALLOW region (higher `allow_min_resonance`, stricter `effect_risk_min_score` when set).
- **If removed:** Only default `PolicyThresholds`.

### Divination

- **Meaning:** Uncertainty / review gate: **requires** causal narrative context when enabled, or tightens policy thresholds.
- **Kind:** Schema `DivinationSpec`; policy.
- **Compiles into:** If `require_causal_context: true`, `decide` requires `causal_root_cast_id` in input or raises; else merges `thresholds` overlay.
- **Guarantees:** Explicit failure when causal context missing and required.
- **If removed:** Callers pass causal context manually without enforcement.

### Banishment

- **Meaning:** **Containment** semantics for destructive effects: default rollback expectation and enforced rollback on program nodes when `BanishmentSpec` applies to ritual compilation.
- **Kind:** Schema `BanishmentSpec`; program validation.
- **Compiles into:** `RollbackStrategy` on nodes, `program_validation` warnings for destructive `EffectType` without rollback when banishment strict.
- **Guarantees:** `strict` mode adds validation errors for missing rollback on destructive effects.
- **If removed:** Only generic `RollbackStrategy` on nodes.

### Genesis / Swarm (experimental)

- **Meaning:** Emergent aspects from history; peer vector aggregation — unchanged from core docs.
- **Kind:** Experimental; see `docs/STABILITY.md`.

## Presentation-only (explicit)

### EffectClass (on Sigil)

- **Role:** Selects **casting note** prose in `vermyth/engine/operations/cast.py` (`_CASTING_NOTES`).
- **Does not affect:** `compute_resonance` numeric path (cosine, penalty, ceiling).
- **Operational Effect types** for policy are `EffectType` on `Effect` (`effect_risk` scorer), not `EffectClass`.

### Casting notes / narrative prose

- **Role:** Human-readable strings on `Verdict`; optional display only.

## Protocol constructs

### Semantically dense exchange (`vermyth.io/v1/semantic_bundle`)

- **Kind:** JSON extension (HTTP `task.input`, A2A metadata).
- **Compiles into:** `skill_id` + `input` for `decide`/`cast`/`compile_program` with `arcane_provenance` for inspection.
- **Fallback:** Omit extension; use plain `skill_id` + `input`.

### Bundle manifest `recommendation` (optional, advisory)

- **Kind:** Structured metadata on `SemanticBundleManifest` (`BundleRecommendationSpec`).
- **Purpose:** Deterministic, inspectable hints for which plain `skill_id` + `input` shapes may benefit from adopting a `semantic_bundle` ref. Evaluated only by `recommend_semantic_bundles` / `POST /arcane/recommend`; **never** applied automatically on invoke.
- **Shape:** `target_skills` (e.g. `decide`), human-readable `why_better`, and ordered `tiers` (first match wins). Each tier lists `require_all` rules with explicit `op` names implemented in [`vermyth/arcane/recommend.py`](../../vermyth/arcane/recommend.py) (`RULE_OPS`).
- **Fallback:** Bundles omit `recommendation`; they remain listable and usable without advisory matching.

## Deprecations

- None in this release; decorative items are **labeled**, not removed.
