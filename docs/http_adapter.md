# HTTP adapter

Vermyth exposes a lightweight HTTP surface for non-MCP consumers. Peer-style task dispatch uses the same A2A-shaped types as [docs/a2a.md](a2a.md).

## Run

```bash
python -m vermyth.adapters.http --host 127.0.0.1 --port 7777 --db vermyth.db
```

## Endpoints

- `GET /tools`: returns `TOOL_DEFINITIONS` (same list as MCP `tools/list` for stable tools).
- `POST /tools/<name>`: invokes the same handler used by MCP `tools/call`. Tool names must be allowed by `VermythTools` tool scope (default `*`). If the JSON body includes a **`semantic_bundle`** reference (`bundle_id`, `version`, `params`), it is expanded **before** dispatch using the same logic as `POST /a2a/tasks` ([`resolve_tool_invocation`](../../vermyth/arcane/invoke.py)); the resolved tool may differ from the path segment when the bundle targets another skill (e.g. `cast`). Successful dict-shaped results may include an additive **`arcane_provenance`** field when a bundle was used. Plain JSON without a bundle is unchanged.
- `GET /.well-known/agent.json`: returns an **agent card** JSON document built from `TOOL_DEFINITIONS` (skills mirror tool names). Alias: `GET /.well-known/agent-card.json`. See [docs/a2a.md](a2a.md).
- `POST /a2a/tasks`: accepts a **Task** JSON body (`skill_id`, `input`, optional `task_id`, `messages`). Dispatches to `TOOL_DISPATCH` with `skill_id` as the tool name. Response is a **TaskResult** (`status`, `artifact`, `error`, …). When `VERMYTH_REQUIRE_CAPABILITY_TOKENS=1`, `input` must include a valid `capability_token` (see [docs/a2a.md](a2a.md)).
  - **Idempotency:** send header `Idempotency-Key`; identical body + key returns the cached **TaskResult** (in-process).
  - **Correlation:** `X-Request-ID` or `X-Correlation-ID` is propagated to execution receipts when programs run tools that persist receipts.
- `GET /events?tail=50&type=decide`: returns recent observability events.
- `GET /healthz`: returns `status`, migration count, and current basis version.

## Security and CORS

- Set `VERMYTH_HTTP_TOKEN` to require `Authorization: Bearer <token>` on all endpoints. Successful static-token auth maps to principal `static-token` for receipt audit fields; configure scopes with `VERMYTH_HTTP_SCOPES` (comma-separated, e.g. `tool:*`).
- Optional JWT: install `pip install -e .[auth-jwt]` and set `VERMYTH_JWT_AUDIENCE`, `VERMYTH_JWT_ISSUER`, `VERMYTH_JWT_SECRET` (see `vermyth/adapters/auth.py`).
- Set `VERMYTH_HTTP_CORS=*` (or a specific origin) to emit CORS headers.

## Capability and A2A-related environment variables

These apply to `POST /a2a/tasks` when using the task gateway:

- `VERMYTH_REQUIRE_CAPABILITY_TOKENS`: set to `1` to require `input.capability_token` on every task.
- `VERMYTH_CAPABILITY_SECRET`: shared secret for HMAC verification of capability tokens (development path). For Ed25519 verification, install optional extra `a2a-crypto` and see [docs/a2a.md](a2a.md).

## Optional A2A JSON-RPC (`[a2a]` extra)

Install `pip install -e .[a2a]` and run `vermyth-a2a` (see `vermyth/adapters/a2a_server.py`) for a Starlette JSON-RPC server with canonical `AgentCard` and SDK task operations. This does not replace the default `python -m vermyth.adapters.http` workflow unless you point clients at it. Matrix: [docs/a2a-compatibility.md](a2a-compatibility.md).

## Semantic bundles on `POST /tools/<name>` (optional)

Built-in bundles live under `vermyth/data/arcane/bundles/` (and optional `VERMYTH_ARCANE_BUNDLE_DIR`). They let you send a **short** `semantic_bundle` object instead of spelling out full `intent` + `aspects` every time. Expansion is server-side; plain JSON remains fully supported.

**Bundle-first `decide` (compact):** one call, fewer fields than the expanded equivalent; response may include `arcane_provenance` with `bundle_id` / `bundle_version`.

```bash
curl -X POST http://127.0.0.1:7777/tools/decide \
  -H "Content-Type: application/json" \
  -d '{
    "semantic_bundle": {
      "bundle_id": "coherent_probe",
      "version": 1,
      "params": { "topic": "audit" }
    }
  }'
```

**Plain JSON equivalent (same runtime behavior after expansion):** longer, but no bundle; response has no `arcane_provenance` from bundle expansion.

```bash
curl -X POST http://127.0.0.1:7777/tools/decide \
  -H "Content-Type: application/json" \
  -d '{
    "intent": {
      "objective": "Probe coherence on audit",
      "scope": "semantic_bundle",
      "reversibility": "REVERSIBLE",
      "side_effect_tolerance": "LOW"
    },
    "aspects": ["MIND", "LIGHT"]
  }'
```

MCP `tools/call` with `"name": "decide"` and the same `arguments` objects behaves the same way. Meta-tools **`expand_semantic_bundle`** and **`compile_ritual`** do not pre-expand bundle refs at the transport layer so their argument shapes stay intact.

## Examples

```bash
curl http://127.0.0.1:7777/tools
```

```bash
curl http://127.0.0.1:7777/.well-known/agent.json
```

```bash
curl -X POST http://127.0.0.1:7777/a2a/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "skill_id": "decide",
    "input": {
      "intent": {
        "objective": "Reveal hidden structure",
        "scope": "analysis",
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "LOW"
      },
      "aspects": ["MIND", "LIGHT"]
    }
  }'
```

```bash
curl -X POST http://127.0.0.1:7777/tools/cast \
  -H "Content-Type: application/json" \
  -d '{
    "aspects": ["MIND", "LIGHT"],
    "objective": "Reveal hidden structure",
    "scope": "analysis",
    "reversibility": "REVERSIBLE",
    "side_effect_tolerance": "LOW"
  }'
```

```bash
curl -X POST http://127.0.0.1:7777/tools/decide \
  -H "Content-Type: application/json" \
  -d '{
    "intent": {
      "objective": "Reveal hidden structure",
      "scope": "analysis",
      "reversibility": "REVERSIBLE",
      "side_effect_tolerance": "LOW"
    },
    "aspects": ["MIND", "LIGHT"]
  }'
```
