# Vermyth

**Vermyth** is a Python library and command-line tool that behaves as a small **semantic execution language** for AI-adjacent workflows. You describe a situation as a combination of symbolic **aspects**, declare an **intent** (objective, scope, reversibility, tolerance), and the system **composes** a resolved **sigil**, **evaluates** how well the intent aligns with that sigil’s geometry, and records the outcome. Persistence (the **grimoire**) and remote control (**MCP**) sit on top of the same core types and contracts.

This repository implements the full stack: **typed models**, **composition and resonance engines**, **SQLite storage**, an **MCP stdio server** (JSON-RPC 2.0, no third-party MCP SDK), and a **human-oriented CLI**.

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
| **`VermythCLI`** | `argparse` subcommands: `cast`, `query`, `search`, `inspect`, `seeds` — formatted tables and detail views on stdout; errors on stderr, exit code 1. |

---

## Installation

Requires **Python 3.11+**.

```bash
pip install -e .
```

Declared dependencies (see `pyproject.toml`): **Pydantic v2**, **python-ulid**, **anthropic** (reserved for future integration; the core library does not require calling Anthropic for local casts).

Console entry points after install:

- **`vermyth`** — CLI (`vermyth.cli.main:main`)
- **`vermyth-mcp`** — MCP stdio server (`vermyth.mcp.server:main`)

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

With default configuration, **`main()`** builds a **`CompositionEngine`**, **`Grimoire()`** (default database under `~/.vermyth/grimoire.db`), and **`ResonanceEngine`** with `backend=None`. If **`VERMYTH_BACKEND`** is set in the environment, the server logs that dynamic backend loading is not implemented and continues with partial projection.

Tool names exposed to clients: **`cast`**, **`query`**, **`semantic_search`**, **`inspect`**, **`seeds`** — each backed by **`VermythTools`** when engine and grimoire are configured.

---

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

```
vermyth/
  schema.py           # Data models
  contracts.py        # ABCs for engine, grimoire, MCP, CLI
  data/sigils/        # JSON sigil tables + contradictions
  engine/
    composition.py    # CompositionEngine
    resonance.py      # ResonanceEngine
  grimoire/
    store.py          # Grimoire (SQLite)
    migrations/       # SQL migrations
  mcp/
    protocol.py       # JSON-RPC helpers
    server.py         # VermythMCPServer
    tools.py          # VermythTools (MCP + CLI)
  cli/
    format.py         # Text formatting
    main.py           # VermythCLI
tests/                # pytest suite
pyproject.toml        # Packaging and scripts
```

---

## Tests

```bash
pytest tests/
```

Tests cover schema validation, contracts, composition, resonance, grimoire, MCP protocol and tools, and CLI behavior.

---

## License and upstream

Project metadata and versioning live in **`pyproject.toml`**. For issues and contributions, use the GitHub repository hosting this code.
