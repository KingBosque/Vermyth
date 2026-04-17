# Vermyth

**Vermyth** is a Python library and command-line tool for a machine-native **semantic IR and decision runtime**. You describe situations as symbolic **aspects**, declare an **intent** (objective, scope, reversibility, tolerance), and the system composes a resolved **sigil**, evaluates alignment, and emits explicit decision artifacts. Persistence (the **grimoire**) and remote control (**MCP**) are layered on top of the same core contracts.

This repository implements the full stack: **typed models**, **composition and scoring engines**, **SQLite storage**, an **MCP stdio server** (JSON-RPC 2.0, no third-party MCP SDK), and a **human-oriented CLI**.

Vermyth intentionally separates concerns:

- Internal semantic IR + runtime semantics.
- MCP for tool/resource access.
- Experimental peer-coordination transport that is **not** the public interoperability contract.

See `docs/STABILITY.md` and `docs/adr/0001-vermyth-as-semantic-ir.md` for stability tiers and architecture posture.

---

## Features at a glance

| Layer | Role |
|--------|------|
| **`vermyth.schema`** | Pydantic models: `AspectID`, `Sigil`, `Intent`, `Verdict`, `CastResult`, `GlyphSeed`, `SemanticVector`, `SemanticQuery`, `Lineage`, enums for effect class, verdict type, etc. |
| **`vermyth.contracts`** | Abstract interfaces: `EngineContract`, `GrimoireContract`, `MCPServerContract`, `CLIContract` — stable boundaries for engines, storage, MCP, and CLI. |
| **`CompositionEngine`** | Loads canonical sigil tables from JSON under `vermyth/data/sigils/`, resolves 1–3 aspects to a named sigil with effect class, resonance ceiling, and contradiction severity. |
| **`ResonanceEngine`** | Projects intent into a constraint (and optional semantic) vector, scores **cosine-based resonance** with the sigil, applies contradiction penalties and ceilings, returns a `Verdict` and full `CastResult`. Optional `ProjectionBackend` for richer semantic projection; otherwise projection stays **PARTIAL**. |
| **`Grimoire`** | SQLite persistence: casts, seeds, structured `query`, in-Python **semantic search** (cosine similarity over stored vectors), migrations (`v001`). |
| **`VermythTools`** | Shared tool implementation used by MCP and CLI: cast, query, semantic search, inspect, seeds (serialization to plain dicts). |
| **`VermythMCPServer`** | Stdio MCP: `initialize`, `tools/list`, `tools/call` with JSON-RPC error codes for validation and internal errors. |
| **Session Codec V2 (experimental)** | Optional binary-first transport + session codec (`vermyth.protocol.session_codec`) for research. This is not part of Vermyth's stable public contract. |
| **Swarm evolution (experimental)** | `ResonanceEngine.auto_cast` (self-healing fluid refinement), `swarm_cast` aggregation, and `GossipPayload` sync are available as research modules and are not interoperability commitments. |
| **Triple evolutionary leap** | Semantic program compilation/execution (`SemanticProgram`), emergent aspect genesis (`EmergentAspect` + acceptance flow), and causal semantic graph tooling (`CausalEdge`, `CausalSubgraph`, predictive casting). |
| **`VermythCLI`** | `argparse` subcommands: `cast`, `query`, `search`, `inspect`, `seeds` — formatted tables and detail views on stdout; errors on stderr, exit code 1. |

---

## Installation

Requires **Python 3.11+**.

```bash
pip install -e .
```

Optional LLM projection backend:

```bash
pip install -e .[llm]
```

Optional A2A JSON-RPC server (see `docs/a2a-compatibility.md`):

```bash
pip install -e .[a2a]
```

Optional Ed25519 receipt signing / verification:

```bash
pip install -e .[a2a-crypto]
```

Optional JWT validation for Bearer (`VERMYTH_JWT_*`):

```bash
pip install -e .[auth-jwt]
```

Declared base dependencies (see `pyproject.toml`): **Pydantic v2**, **python-ulid**. The optional `llm` extra installs **anthropic** for `VERMYTH_BACKEND=llm|auto`.

Console entry points after install:

- **`vermyth`** — CLI (`vermyth.cli.main:main`)
- **`vermyth-mcp`** — MCP stdio server (`vermyth.mcp.server:main`)
- **`vermyth-a2a`** — optional A2A JSON-RPC edge (`vermyth.adapters.a2a_server:main`), requires `pip install -e .[a2a]`

## Consumers

- **CLI**: `vermyth ...` for human-readable workflows.
- **MCP**: `vermyth-mcp` for JSON-RPC agent integrations.
- **HTTP**: `python -m vermyth.adapters.http` for lightweight tool-style HTTP calls.
  See [`docs/http_adapter.md`](docs/http_adapter.md) for endpoint details.
- **A2A (optional)**: standards-shaped JSON-RPC + agent card when using the `[a2a]` extra; compatibility notes in [`docs/a2a-compatibility.md`](docs/a2a-compatibility.md). The legacy `POST /a2a/tasks` shim remains the default HTTP path.

### V1 compatibility vs V2 sessions (experimental track)

- **V1 (default)**: MCP is **newline-delimited JSON-RPC 2.0** (`initialize`, `tools/list`, `tools/call`). The V1 “geometric” packet helpers (`vermyth.mcp.geometric`) remain **lossy** by design.
- **V2 (optional, experimental)**: A session layer with **canonical packets** and **replay protection**:
  - `SessionRecord`, `CanonicalPacketV2`, `CanonicalResponseV2` in `vermyth.schema`
  - Persistence in the grimoire (`v008_sessions.sql`)
  - Codec helpers in `vermyth.protocol.session_codec`
  - Optional **binary framing** in the MCP server when `VERMYTH_BINARY_TRANSPORT=1`

### Swarm and federation (experimental track)

- **`auto_cast`** (`vermyth` CLI / MCP `auto_cast`): iteratively blends the semantic vector toward the fluid sigil until the verdict reaches `target_resonance` or `max_depth`.
- **Swarms** (`swarm_join`, `swarm_cast`, `swarm_status`): peers share a `swarm_id`; vectors are aggregated with weights `1 + 0.01 * min(100, coherence_streak)`.
- **Gossip** (`gossip_sync` / binary frames `GOSSIP_PUSH` / `GOSSIP_PULL`): JSON payload signed with `sign_gossip_payload`; set **`VERMYTH_FEDERATION_SECRET`** for verification.
- These features are experimental and not the wire-level standard Vermyth recommends for production interoperability.

### Semantic programs

- **`SemanticProgram`** defines a DAG of `CastNode`s (`CAST`, `FLUID_CAST`, `AUTO_CAST`, `GATE`, `MERGE`).
- Compile with MCP/CLI (`compile_program`, `compile-program`) to validate graph integrity, run static validation (effects, retries, postconditions), and mark `COMPILED`. Responses include a `validation` object with warnings. Set `VERMYTH_DENY_PROGRAM_VALIDATION_WARNINGS=1` to refuse execution when warnings are present.
- Execute with (`execute_program`, `execute-program`) to produce a `ProgramExecution` with node->cast mapping and branch lineage.
- Persisted in grimoire migration **`v010_semantic_programs.sql`** (`programs`, `program_executions`).

### Arcane semantic layer (optional)

- **`vermyth.arcane`** maps ritual / ward / divination / banishment vocabulary to real behavior: bundle compilation, policy merges, program metadata, and provenance on receipts. Plain `skill_id` + `input` remains the baseline; **`semantic_bundle`** in task input (or the A2A extension URI) is optional and expands server-side.
- **Discover bundles first (recommended):** use MCP **`list_semantic_bundles`** or HTTP **`GET /arcane/bundles`** to see built-in bundles (summaries, `target_skill`, `param_keys`). Use **`inspect_semantic_bundle`** or **`GET /arcane/bundles/{bundle_id}?version=1`** to see the manifest plus a **compiled preview** (what tool and arguments it becomes—no black box). MCP resources: `vermyth://semantic_bundles` and `vermyth://semantic_bundle/{bundle_id}?version=1`.
- **Recommend bundles (advisory):** MCP **`recommend_semantic_bundles`** or HTTP **`POST /arcane/recommend`** with `{ "skill_id", "input" }` returns **inspectable** matches (`strength`, `match_kind`, `matched_features`, `why_better`) for plain JSON—**no execution**, never rewrites your request. Matching is **primarily manifest-driven**: each bundle may declare a **`recommendation`** block in its JSON (`target_skills`, ordered `tiers`, declarative rules). Use a higher `min_strength` (optional) to filter weak hints. Catalog rows from **`list_semantic_bundles`** / **`GET /arcane/bundles`** include a compact **`recommendation`** hint when present.
- **Canonical bundle-first flows** (then plain JSON equivalents in [`docs/http_adapter.md`](docs/http_adapter.md) and [`docs/specs/arcane-design-summary.md`](docs/specs/arcane-design-summary.md)):
  - **`coherent_probe`** — default `decide` probe with MIND+LIGHT; fewer fields than spelling `intent` + `aspects`; adds `arcane_provenance` when used.
  - **`strict_ward_probe`** — same shape with **stricter policy thresholds** (ward) without hand-merging `PolicyThresholds`.
  - **`divination_gate`** — **requires `causal_root_cast_id`** when executing `decide` (divination/review gate); fail-fast without causal context.
- MCP tools: **`list_semantic_bundles`**, **`inspect_semantic_bundle`**, **`recommend_semantic_bundles`**, **`expand_semantic_bundle`**, **`compile_ritual`**. Operational spec: [`docs/specs/ontology.md`](docs/specs/ontology.md); design digest: [`docs/specs/arcane-design-summary.md`](docs/specs/arcane-design-summary.md).

### Emergent aspect genesis

- `ResonanceEngine.propose_genesis(...)` analyzes coherent cast history and proposes `EmergentAspect` candidates.
- Proposals are stored in **`v011_emergent_aspects.sql`** and exposed by tools/CLI:
  - `propose_genesis`, `genesis_proposals`, `accept_genesis`, `reject_genesis`
  - `propose-genesis`, `genesis-proposals`, `accept-genesis`, `reject-genesis`
- Accepting a proposal registers a concrete `RegisteredAspect` and extends semantic dimensionality.

### Causal semantic graphs

- Typed causal edges: `CAUSES`, `INHIBITS`, `ENABLES`, `REQUIRES` (`CausalEdgeType`).
- Graph traversal via `CausalQuery` -> `CausalSubgraph`, with narrative coherence scoring.
- Predictive casting uses causal context to seed `auto_cast`.
- Persisted in **`v012_causal_graph.sql`** (`causal_edges`) with MCP/CLI support:
  - `infer_causal_edge`, `add_causal_edge`, `causal_subgraph`, `evaluate_narrative`, `predictive_cast`
  - `infer-cause`, `add-cause`, `causal-graph`, `evaluate-narrative`, `predictive-cast`
- Binary transport adds frame type `CAUSAL_SYNC` for causal edge federation sync.

---

## Core concepts

### Aspects and sigils

- **`AspectID`** — Six primary aspects (`VOID`, `FORM`, `MOTION`, `MIND`, `DECAY`, `LIGHT`) with polarity and entropy metadata.
- A **sigil** is the resolved meaning of **one to three** aspects, loaded from bundled JSON tables (`canonical_single.json`, `canonical_dual.json`, `canonical_triple.json`, plus optional `extended/`), with **contradiction** metadata from `contradictions.json`.
- Each sigil has an **`EffectClass`**, **`SemanticVector`** (six components in canonical aspect order), **fingerprint**, and **polarity** derived from the aspect set.

### Intent and verdict

- **`Intent`** — `objective`, `scope`, `reversibility`, `side_effect_tolerance` (bounded strings and enums).
- **`ResonanceEngine.evaluate`** builds an **`IntentVector`**, compares it to the sigil vector, applies **HARD/SOFT** contradiction penalties from the table, caps by **`resonance_ceiling`**, and classifies **`VerdictType`**: COHERENT (≥ 0.75 adjusted), PARTIAL (≥ 0.45), else INCOHERENT (with structured proof text and optional incoherence reason).

### Cast results and seeds

- **`CastResult`** — Immutable record: ULID `cast_id`, timestamp, intent, sigil, verdict, optional `lineage`, optional `glyph_seed_id`.
- **`GlyphSeed`** — Running statistics for an aspect pattern: `observed_count`, `mean_resonance`, `coherence_rate`, optional `candidate_effect_class`, `crystallized`, plus a vector aligned to the pattern.
- **`ResonanceEngine.accumulate`** updates or creates a seed from a cast; **`crystallize`** can promote a mature seed into a derived **`Sigil`** when thresholds are met (caller persists via grimoire).

### Semantic query and search

- **`SemanticQuery`** — Field filters (`verdict_filter`, `effect_class_filter`, `min_resonance`, `branch_id`, `aspect_filter`, `limit`, …) plus optional **`proximity_to`** + **`proximity_threshold`** for similarity search.
- **`Grimoire.semantic_search`** loads stored cast vectors and ranks by **cosine similarity** in Python (no vector DB).

---

## Command-line interface (`vermyth`)

The CLI calls **`VermythTools`** directly (same behavior as MCP tools), prints **human-readable** text (tables and detail blocks from `vermyth.cli.format`), and never speaks JSON to the user.

### `cast`

Compose aspects and evaluate against an intent; persists cast and seed side effects through the tool layer.

```bash
vermyth cast --aspects MIND LIGHT \
  --objective "Study the pattern" \
  --scope "local workspace" \
  --reversibility REVERSIBLE \
  --side-effect-tolerance HIGH
```

### `query`

Query the grimoire with optional filters (`--verdict`, `--min-resonance`, `--branch-id`, `--limit`).

```bash
vermyth query --limit 20
vermyth query --verdict COHERENT --min-resonance 0.5
```

### `search`

Semantic proximity search: six floats (VOID … LIGHT order), threshold, limit.

```bash
vermyth search --vector 0.1 0.2 0 0 0 0 --threshold 0.3 --limit 10
```

### `inspect`

Show one cast by `cast_id`.

```bash
vermyth inspect 01HXYZ...
```

### `seeds`

List glyph seeds; optional `--crystallized` or `--accumulating`.

```bash
vermyth seeds
vermyth seeds --accumulating
```

Errors go to **stderr**; the process exits with **1** on failure. Missing or invalid arguments use argparse’s normal exit code (**2**).

---

## MCP server (`vermyth-mcp`)

Runs a **newline-delimited JSON-RPC 2.0** server on stdio (protocol subset: `initialize`, `notifications/initialized`, `tools/list`, `tools/call`). **Stderr** is for logs only.

With default configuration, **`main()`** builds a **`CompositionEngine`**, **`Grimoire()`** (default database under `~/.vermyth/grimoire.db`), and **`ResonanceEngine`** with env-driven backend selection (defaults to partial projection).

Tool names exposed to clients focus on decision/casting/query/program/grimoire workflows. Experimental session/sync families are not part of the stable MCP contract. See `TOOL_DEFINITIONS` in `vermyth/mcp/tool_definitions.py` for the authoritative list.

### Experimental tools (gated)

Set **`VERMYTH_EXPERIMENTAL_TOOLS=1`** to include additional tools in MCP `tools/list`, HTTP `GET /tools`, and `GET /.well-known/agent.json`. Today this adds the **swarm** family (`swarm_join`, `swarm_cast`, `swarm_status`, `auto_cast`, `gossip_sync`, and related definitions in `vermyth/mcp/tools/swarm.py`). Leave unset for the default stable tool surface. See `docs/STABILITY.md`.

---

## Projection backends (env configuration)

Vermyth can optionally project intent text into aspect space using a selectable backend. This affects cast semantic quality; when unavailable or misconfigured, Vermyth will fall back without crashing.

Environment variables:

- **`VERMYTH_BACKEND`**: `none` | `local` | `embed` | `llm` | `auto` (default: `none`)
  - **`none`**: no semantic projection (constraint-only, `ProjectionMethod.PARTIAL`)
  - **`local`**: deterministic keyword-based projection
  - **`embed`**: embedding-based projection (install optional extra: `pip install -e .[embed]`)
  - **`llm`**: LLM projection only (errors if misconfigured)
  - **`auto`**: try LLM projection; on failure fall back (see `VERMYTH_FALLBACK`)
- **`VERMYTH_PROVIDER`**: provider id for `llm` / `auto` (default: `anthropic`)
- **`VERMYTH_MODEL`**: provider model string (default: `claude-3-5-sonnet-latest`)
- **`VERMYTH_ANTHROPIC_API_KEY`**: Anthropic API key (preferred for `anthropic`)
- **`VERMYTH_API_KEY`**: generic API key fallback (used if provider-specific key not set)
- **`VERMYTH_FALLBACK`**: `local` | `none` (default: `local`)
- **`VERMYTH_TIMEOUT_S`**: float seconds (default: `10`)
- **`VERMYTH_EMBED_MODEL`**: sentence-transformers model id (default: `all-MiniLM-L6-v2`)

Examples:

```bash
# Deterministic local projection
set VERMYTH_BACKEND=local
vermyth cast --aspects MIND LIGHT --objective "Study the pattern" --scope "repo" --reversibility REVERSIBLE --side-effect-tolerance HIGH

# LLM projection with local fallback
set VERMYTH_BACKEND=auto
set VERMYTH_PROVIDER=anthropic
set VERMYTH_ANTHROPIC_API_KEY=...
set VERMYTH_FALLBACK=local
vermyth-mcp
```

## Programmatic use

Minimal in-process cast (no grimoire):

```python
from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.schema import AspectID, Intent, ReversibilityClass, SideEffectTolerance

composition = CompositionEngine()
engine = ResonanceEngine(composition, backend=None)
intent = Intent(
    objective="Align the workspace",
    scope="session",
    reversibility=ReversibilityClass.REVERSIBLE,
    side_effect_tolerance=SideEffectTolerance.HIGH,
)
result = engine.cast(frozenset({AspectID.MIND, AspectID.LIGHT}), intent)
print(result.verdict.verdict_type, result.verdict.resonance.adjusted)
```

With persistence, construct **`Grimoire(db_path=...)`** and **`VermythTools(engine, grimoire)`**, or use **`VermythMCPServer(engine=..., grimoire=...)`** for tests.

---

## Project layout

```text
vermyth/
  schema.py                 # Data models
  contracts.py              # ABCs for engine, grimoire, MCP, CLI
  data/sigils/              # JSON sigil tables + contradictions
  engine/
    composition.py          # CompositionEngine
    resonance.py            # ResonanceEngine facade
    operations/             # Engine family modules
  grimoire/
    store.py                # Grimoire facade
    repositories/           # Persistence family repositories
    migrations/             # SQL migrations
  mcp/
    protocol.py             # JSON-RPC helpers
    tool_definitions.py     # TOOL_DEFINITIONS registry
    server.py               # VermythMCPServer facade + dispatch
    tools/
      facade.py             # VermythTools class
      *.py                  # Family tool modules + serializers
  cli/
    format.py               # Text formatting
    parser.py               # Parser + command router
    main.py                 # VermythCLI facade
    commands/               # Family command modules
tests/                      # pytest suite
pyproject.toml              # Packaging and scripts
```

---

## Tests

```bash
pytest tests/
```

Tests cover schema validation, contracts, composition, resonance, grimoire, MCP protocol and tools, and CLI behavior.

## Benchmarks

- `benchmarks/corpus_v0_synthetic.json` is a regression fixture, not a frontier performance claim.
- External dry-run adapters live under `benchmarks/adapters/` (`osworld.py`, `webarena.py`) and are intended as a bridge toward realistic task evaluation.
- A **real** minimal harness (`benchmarks/run_external.py`) records outbound HTTP + policy decisions under `benchmarks/artifacts/`. See [`docs/benchmarks.md`](docs/benchmarks.md) and `benchmarks/report.md`.

---

## License and upstream

Project metadata and versioning live in **`pyproject.toml`**. For issues and contributions, use the GitHub repository hosting this code.
