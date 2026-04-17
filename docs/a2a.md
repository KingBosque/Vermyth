# A2A-shaped adapter

Vermyth exposes a minimal **outer boundary** for agent-style task exchange in `vermyth/adapters/a2a/`. The default HTTP surface is a simple JSON task API (`POST /a2a/tasks`). For a **standards-aligned** JSON-RPC + SDK path (`a2a-sdk`), optional extra **`[a2a]`** and compatibility notes, see [`docs/a2a-compatibility.md`](a2a-compatibility.md).

## Agent card

`GET /.well-known/agent.json` (and `/.well-known/agent-card.json`) returns a JSON object:

- `name`, `version`, `description`
- `skills`: list of `{ id, name, description }` derived from MCP `TOOL_DEFINITIONS` (each tool name is a skill id).

The optional SDK builds a richer `AgentCard` (capabilities, security schemes, extensions) when using `vermyth-a2a` — see [`docs/a2a-compatibility.md`](a2a-compatibility.md).

## Task dispatch

`POST /a2a/tasks` (or in-process `TaskGateway.execute_task`) expects a JSON body matching **Task**:

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string (optional) | Defaults to a new ULID if omitted. |
| `skill_id` | string | **Required.** Must match a Vermyth tool name (e.g. `decide`, `cast`). |
| `input` | object | **Required.** Passed to the tool handler as `arguments` (same shape as MCP `tools/call`). |
| `messages` | array (optional) | Reserved for future use. |

Send **`Idempotency-Key`** on HTTP to reuse a prior result for the same payload (replay-safe retries).

**Semantic bundles:** `input` may include `semantic_bundle` (`bundle_id`, `version`, `params`); the gateway expands it before dispatch (same as [`resolve_tool_invocation`](../vermyth/arcane/invoke.py)). MCP `tools/call` and HTTP `POST /tools/<name>` use the same expansion so bundle behavior matches tasks. List and inspect available bundles via MCP `list_semantic_bundles` / `inspect_semantic_bundle`, MCP resources `vermyth://semantic_bundles`, or HTTP `GET /arcane/bundles` — see [`docs/http_adapter.md`](http_adapter.md). For plain task `input`, MCP `recommend_semantic_bundles` or HTTP `POST /arcane/recommend` suggests matching bundles using manifest-declared rules, with inspectable reasons and **`guided_upgrade`** (copy-paste `semantic_bundle` + inspect paths) (advisory only).

Response shape **TaskResult**:

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string | Echo of the task id. |
| `status` | string | `queued`, `running`, `completed`, or `failed`. |
| `artifact` | object or null | On success, wraps the tool result in `{ content: <tool_result> }`. |
| `error` | string or null | Error message when `status` is `failed`. |
| `updated_at` | ISO datetime | Server timestamp. |

## Capability tokens

When `VERMYTH_REQUIRE_CAPABILITY_TOKENS=1`, `input` must include `capability_token`, a JSON object with:

| Field | Type | Description |
| --- | --- | --- |
| `holder` | string | Identity of the caller. |
| `tool_scope` | string | Glob pattern; must match `skill_id` (e.g. `decide` or `*`). |
| `expiry` | ISO datetime | Token must not be expired. |
| `issuer` | string | Issuer id. |
| `algorithm` | string | **`HMAC_SHA256`** for HMAC-SHA256 over the canonical pipe-separated material (hex digest). **`ED25519`** for Ed25519 over the same bytes: set `VERMYTH_CAPABILITY_ED25519_PUBLIC_KEY` to a PEM public key and use a **base64** signature; if only `VERMYTH_CAPABILITY_SECRET` is set, verification falls back to HMAC for development. |
| `signature` | string | Hex digest (HMAC) or standard base64 (Ed25519). |

Environment:

- `VERMYTH_CAPABILITY_SECRET`: shared secret for **HMAC_SHA256** (and optional HMAC fallback for `algorithm=ED25519` when no public key is configured).
- For **Ed25519** verification: `pip install -e .[a2a-crypto]` and set **`VERMYTH_CAPABILITY_ED25519_PUBLIC_KEY`** to the PEM-encoded public key.

## Code references

- Types: [vermyth/adapters/a2a/types.py](../vermyth/adapters/a2a/types.py)
- Gateway: [vermyth/adapters/a2a/gateway.py](../vermyth/adapters/a2a/gateway.py)
- Verification: [vermyth/adapters/a2a/security.py](../vermyth/adapters/a2a/security.py)
