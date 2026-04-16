# HTTP adapter

Vermyth exposes a lightweight HTTP surface for non-MCP consumers.

## Run

```bash
python -m vermyth.adapters.http --host 127.0.0.1 --port 7777 --db vermyth.db
```

## Endpoints

- `GET /tools`: returns `TOOL_DEFINITIONS`.
- `POST /tools/<name>`: invokes the same handler used by MCP `tools/call`.
- `GET /events?tail=50&type=decide`: returns recent observability events.
- `GET /healthz`: returns `status`, migration count, and current basis version.

## Security and CORS

- Set `VERMYTH_HTTP_TOKEN` to require `Authorization: Bearer <token>`.
- Set `VERMYTH_HTTP_CORS=*` (or a specific origin) to emit CORS headers.

## Examples

```bash
curl http://127.0.0.1:7777/tools
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
