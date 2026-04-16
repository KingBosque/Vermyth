# HTTP adapter

Vermyth exposes a lightweight HTTP surface for non-MCP consumers. Peer-style task dispatch uses the same A2A-shaped types as [docs/a2a.md](a2a.md).

## Run

```bash
python -m vermyth.adapters.http --host 127.0.0.1 --port 7777 --db vermyth.db
```

## Endpoints

- `GET /tools`: returns `TOOL_DEFINITIONS` (same list as MCP `tools/list` for stable tools).
- `POST /tools/<name>`: invokes the same handler used by MCP `tools/call`. Tool names must be allowed by `VermythTools` tool scope (default `*`).
- `GET /.well-known/agent.json`: returns an **agent card** JSON document built from `TOOL_DEFINITIONS` (skills mirror tool names). See [docs/a2a.md](a2a.md).
- `POST /a2a/tasks`: accepts a **Task** JSON body (`skill_id`, `input`, optional `task_id`, `messages`). Dispatches to `TOOL_DISPATCH` with `skill_id` as the tool name. Response is a **TaskResult** (`status`, `artifact`, `error`, …). When `VERMYTH_REQUIRE_CAPABILITY_TOKENS=1`, `input` must include a valid `capability_token` (see [docs/a2a.md](a2a.md)).
- `GET /events?tail=50&type=decide`: returns recent observability events.
- `GET /healthz`: returns `status`, migration count, and current basis version.

## Security and CORS

- Set `VERMYTH_HTTP_TOKEN` to require `Authorization: Bearer <token>` on all endpoints.
- Set `VERMYTH_HTTP_CORS=*` (or a specific origin) to emit CORS headers.

## Capability and A2A-related environment variables

These apply to `POST /a2a/tasks` when using the task gateway:

- `VERMYTH_REQUIRE_CAPABILITY_TOKENS`: set to `1` to require `input.capability_token` on every task.
- `VERMYTH_CAPABILITY_SECRET`: shared secret for HMAC verification of capability tokens (development path). For Ed25519 verification, install optional extra `a2a-crypto` and see [docs/a2a.md](a2a.md).

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
