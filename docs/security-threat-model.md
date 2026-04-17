# Vermyth Threat Model

## Scope

This document covers plan-level security concerns for Vermyth as a semantic IR runtime with MCP and A2A-style adapters.

## Threat assumptions

- Message channels are attack surfaces (agent-in-the-middle, replay, substitution).
- `intent.objective` and other text fields can carry prompt-injection payloads.
- Tool calls can escalate authority if scope checks are missing.
- Session and federation metadata can be forged when proof/signature checks are weak.
- Genesis proposals can be poisoned by adversarial histories.

## Primary controls

- Capability-token checks for A2A task execution (`VERMYTH_REQUIRE_CAPABILITY_TOKENS=1`).
- Least-authority tool scoping via `VermythTools(..., allowed_tool_scope=[...])` and HTTP scope lists (`VERMYTH_HTTP_SCOPES`) when using static Bearer.
- Replay-aware session state for experimental codec paths.
- Explicit stable-vs-experimental boundaries in `docs/STABILITY.md`.
- **Idempotency-Key** on `POST /a2a/tasks` to deduplicate identical task payloads (in-process cache).
- Optional **JWT** Bearer validation (`pip install -e .[auth-jwt]`, `VERMYTH_JWT_*`) via `resolve_principal` in `vermyth/adapters/auth.py`.
- **Execution receipts:** optional Ed25519 signatures (`VERMYTH_RECEIPT_SIGNING_KEY`), verification via MCP `verify_execution_receipt` or CLI `receipt-verify` with `VERMYTH_RECEIPT_VERIFY_PUBLIC_KEY` / PEM file; correlation and principal ids on persisted rows (migration `v020`).
- **Instruction vs data:** treat inbound A2A/MCP text as untrusted; do not blindly concatenate user-controlled parts into `intent.objective` without an explicit join policy. Optional low-trust handling in the SDK executor (`VERMYTH_DENY_LOW_TRUST_INVOKE`).

## Production vs development

- **Production-style:** OAuth2/JWT or well-scoped Bearer tokens; asymmetric capability proofs where possible; receipt signing for cross-agent handoff.
- **Development:** shared `VERMYTH_HTTP_TOKEN`, HMAC capability tokens (`VERMYTH_CAPABILITY_SECRET`), optional Ed25519 for capabilities (`VERMYTH_CAPABILITY_ED25519_PUBLIC_KEY`).

## Gaps / residual risk

- Full instruction/data separation and taint propagation across all tools is not complete; policy hooks exist for programs and A2A extensions.
- Expand fuzzing around adapter inputs, resource URIs, and JWT edge cases.
- SSE / streaming bindings are out of scope; do not expose unauthenticated stream endpoints when added.
