# Changelog

## Unreleased

### Interoperability

- Optional **A2A** stack: `pip install -e .[a2a]` (`a2a-sdk`, `uvicorn`), CLI `vermyth-a2a`, SDK `AgentCard` + JSON-RPC app (`vermyth/adapters/a2a/sdk_factory.py`, `vermyth/adapters/a2a_server.py`).
- Legacy HTTP: `POST /a2a/tasks` supports **Idempotency-Key**, **X-Request-ID** / **X-Correlation-ID**; correlation and optional principal flow to execution receipts.

### Security

- `AuthPrincipal` / `resolve_principal` (`vermyth/adapters/auth.py`): static Bearer, optional JWT (`[auth-jwt]`).
- Execution receipts: optional **Ed25519** signing (`VERMYTH_RECEIPT_SIGNING_KEY`), DB columns via migration `v020`, MCP `verify_execution_receipt`, CLI `vermyth receipt-verify`.
- Program compile-time **validation** report; optional `VERMYTH_DENY_PROGRAM_VALIDATION_WARNINGS=1` blocks execution when warnings remain.

### Benchmarks

- `benchmarks/run_external.py`: real HTTP + `tool_decide` artifact JSON under `benchmarks/artifacts/`.

### Documentation

- See `docs/a2a-compatibility.md`, `docs/benchmarks.md`, and updates to `docs/security-threat-model.md`, `docs/http_adapter.md`, `docs/a2a.md`, `docs/STABILITY.md`, README.
