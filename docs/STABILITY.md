# Stability Matrix

This document is the source of truth for Vermyth public-surface stability.

## Stable

- `vermyth.engine`
- `vermyth.schema`
- `vermyth.grimoire`
- `vermyth.contracts`
- `vermyth.cli`
- `vermyth.adapters.http`
- `vermyth.mcp.server`
- `vermyth.mcp.tool_definitions`
- `vermyth.mcp.tools.casting`
- `vermyth.mcp.tools.query`
- `vermyth.mcp.tools.seeds`
- `vermyth.mcp.tools.decisions`
- `vermyth.mcp.tools.programs`
- `vermyth.mcp.tools.causal`
- `vermyth.mcp.tools.drift`
- `vermyth.mcp.tools.registry`
- `vermyth.mcp.tools.observability`
- `vermyth.arcane` (ontology types, bundle compiler, optional `semantic_bundle` expansion)
- `vermyth.mcp.tools.arcane` (`expand_semantic_bundle`, `compile_ritual`, `list_semantic_bundles`, `inspect_semantic_bundle`, `recommend_semantic_bundles`, `get_bundle_adoption_telemetry`, `get_bundle_adoption_report`)

## Experimental

- `vermyth.protocol.session_codec`
- `vermyth.engine.operations.swarm`
- `vermyth.mcp.tools.swarm`
- `vermyth.mcp.tools.session`
- `vermyth.mcp.binary_transport`
- `vermyth.mcp.geometric`
- `vermyth.mcp.tools.genesis` (experimental but reviewed)
- `vermyth.adapters.a2a_server` and `vermyth.adapters.a2a.sdk_factory` (optional `[a2a]` JSON-RPC surface; legacy `vermyth.adapters.http` remains stable)

### Gated experimental tools

When **`VERMYTH_EXPERIMENTAL_TOOLS=1`**, MCP and HTTP also expose the swarm tool definitions (`vermyth/mcp/tools/swarm`). Default is off so the stable tool list matches production expectations.

## Deferred

- Full A2A spec coverage (SSE, gRPC, push) — see `docs/a2a-compatibility.md`.
- Turnkey OSWorld/WebArena drivers in-repo (`bench-real` extra is a placeholder; `benchmarks/run_external.py` provides one real network path).

See `docs/adr/0001-vermyth-as-semantic-ir.md` for rationale and boundary decisions. See `docs/http_adapter.md`, `docs/a2a.md`, and `docs/a2a-compatibility.md` for HTTP/A2A surfaces.
