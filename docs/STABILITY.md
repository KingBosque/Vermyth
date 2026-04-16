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

## Experimental

- `vermyth.protocol.session_codec`
- `vermyth.engine.operations.swarm`
- `vermyth.mcp.tools.swarm`
- `vermyth.mcp.tools.session`
- `vermyth.mcp.binary_transport`
- `vermyth.mcp.geometric`
- `vermyth.mcp.tools.genesis` (experimental but reviewed)

### Gated experimental tools

When **`VERMYTH_EXPERIMENTAL_TOOLS=1`**, MCP and HTTP also expose the swarm tool definitions (`vermyth/mcp/tools/swarm`). Default is off so the stable tool list matches production expectations.

## Deferred

- Deeper A2A protocol parity beyond the current JSON task gateway (`POST /a2a/tasks`, `GET /.well-known/agent.json`).
- Optional Ed25519 capability verification (`pip install -e .[a2a-crypto]`); HMAC remains the default dev path.
- Real-environment benchmark adapters (OSWorld/WebArena integration mode; dry-run scaffolding exists under `benchmarks/adapters/`).

See `docs/adr/0001-vermyth-as-semantic-ir.md` for rationale and boundary decisions. See `docs/http_adapter.md` and `docs/a2a.md` for the HTTP/A2A surface.
