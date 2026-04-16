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
- Least-authority tool scoping via `VermythTools(..., allowed_tool_scope=[...])`.
- Replay-aware session state for experimental codec paths.
- Explicit stable-vs-experimental boundaries in `docs/STABILITY.md`.

## Gaps / follow-ups

- Replace shared-secret token proof with asymmetric Ed25519 keypairs.
- Add stronger instruction/data separation at tool boundary.
- Add signed provenance receipts for cross-agent artifact exchange.
- Expand fuzzing around adapter inputs and resource URIs.

