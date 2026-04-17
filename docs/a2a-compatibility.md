# A2A compatibility matrix

Vermyth aligns its **edge** with the [A2A specification](https://github.com/a2aproject/A2A) where practical, without claiming full conformance for every binding.

## Spec alignment

| Item | Version / notes |
| --- | --- |
| Normative reference | A2A data model concepts: Task, Message, Part, Artifact, extensions |
| Python SDK (optional) | `a2a-sdk[http-server]` pinned in `[project.optional-dependencies]` **a2a** (`pyproject.toml`) |
| Default HTTP server | Legacy `python -m vermyth.adapters.http`: `POST /a2a/tasks`, `GET /.well-known/agent.json` |

## Supported operations

| Operation | Legacy HTTP | Optional JSON-RPC (`vermyth-a2a`) |
| --- | --- | --- |
| Task dispatch / send | `POST /a2a/tasks` → `TaskResult` (sync completion) | **SendMessage** via SDK handler (in-memory task store) |
| Get task | Not exposed (sync-only path) | **GetTask** via SDK store (when `[a2a]` installed) |
| Cancel task | Not implemented on legacy gateway | **CancelTask** best-effort / documented subset |
| Agent card | `GET /.well-known/agent.json` (+ `agent-card.json`) | SDK `AgentCard` from `build_sdk_agent_card` |

## Bindings

| Binding | Status |
| --- | --- |
| JSON POST task API | Supported (`/a2a/tasks`) |
| JSON-RPC + Starlette (SDK) | Optional: `pip install -e .[a2a]`, entry point `vermyth-a2a` |
| SSE streaming | Not supported |
| gRPC | Not supported |
| Push webhooks | Not supported |

## Extensions (Vermyth namespace)

Vermyth-specific payloads use explicit extension URIs (see `vermyth/adapters/a2a/extensions.py`), for example:

- `vermyth.io/v1/invoke` — tool invocation metadata
- `vermyth.io/v1/execution_receipt` — receipt references where applicable
- `vermyth.io/v1/semantic_bundle` — optional named semantic bundle for task input; server expands to `skill_id` + `input` (see `docs/specs/ontology.md`)

Do not overload core Task/Message fields with Vermyth-only data.

## Authentication

- **Development:** `VERMYTH_HTTP_TOKEN` (Bearer) on HTTP; capability tokens on task paths when `VERMYTH_REQUIRE_CAPABILITY_TOKENS=1`.
- **SDK agent card:** Bearer security scheme appears when `VERMYTH_HTTP_TOKEN` or `VERMYTH_A2A_REQUIRE_BEARER=1` is set.
- **Optional JWT:** `pip install -e .[auth-jwt]` and `VERMYTH_JWT_*` variables; see `vermyth/adapters/auth.py` and `docs/security-threat-model.md`.

## Not supported (honest gaps)

- Full SSE streaming (v1)
- Push subscriptions
- All transports from the spec matrix unless listed above
- Durable task store for legacy HTTP (default is synchronous completion in-process)

For the minimal JSON task shim, see [`docs/a2a.md`](a2a.md).
