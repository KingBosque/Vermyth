# Vermyth (TypeScript)

Side-by-side TypeScript package for Node-based agents and tooling. Python under `vermyth/` remains the behavioral oracle. **Golden JSON fixtures** lock **wire shapes** for fixed inputs only—they do not claim full runtime parity with Python.

## Requirements

- **Node.js 20.x** (matches [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) `setup-node`; `package.json` allows `>=20`).

## Setup

```bash
cd typescript
npm ci
npm run sync-assets
```

`sync-assets` copies shared JSON data and SQL migrations from `vermyth/data/` and `vermyth/grimoire/migrations/` into `typescript/assets/` (see [`scripts/sync-assets.mjs`](scripts/sync-assets.mjs)).

## Commands

| Script        | Purpose                          |
|---------------|----------------------------------|
| `npm run lint`| ESLint on `src/`                 |
| `npm run build` | TypeScript compile + assets    |
| `npm test`    | Vitest                           |

## Binaries (`npm link` / `npx` after build)

| Binary            | Role        |
|-------------------|------------|
| `vermyth-ts`     | CLI        |
| `vermyth-mcp-ts` | MCP server |
| `vermyth-http-ts`| HTTP adapter |

## Parity: what is proven (goldens)

Committed fixtures are asserted in Vitest with **exact deep equality** after `JSON.parse` (same pattern for all goldens below).

| Surface | Python oracle | TS fixture | Test |
|---------|----------------|------------|------|
| MCP cast summary (`cast_result_to_dict`) | `vermyth/mcp/tools/casting/_legacy.py` | [`src/mcp/fixtures/cast-result-golden.json`](src/mcp/fixtures/cast-result-golden.json) | [`src/mcp/cast-result-json.golden.test.ts`](src/mcp/cast-result-json.golden.test.ts) |
| MCP `decide` decision — **ALLOW** (`policy_decision_to_dict`) | `vermyth/mcp/tools/_serializers.py` | [`src/mcp/fixtures/policy-decision-golden.json`](src/mcp/fixtures/policy-decision-golden.json) | [`src/mcp/policy-decision-json.golden.test.ts`](src/mcp/policy-decision-json.golden.test.ts) |
| MCP `decide` decision — **RESHAPE** with `suggested_intent` | same | [`src/mcp/fixtures/policy-decision-reshape-golden.json`](src/mcp/fixtures/policy-decision-reshape-golden.json) | same test file (second case) |

Together, the two policy-decision goldens cover the serializer branches **`suggested_intent: null`** (ALLOW) and **non-null nested intent object** (RESHAPE), including `objective`, `scope`, `reversibility`, and `side_effect_tolerance` in wire JSON.

**Python remains authoritative** for live policy outcomes from `decide()`, engine behavior, and any serializer change meant to track Python. Goldens only prove **stable MCP decision JSON** for hand-built `PolicyDecision` values.

### Optional: compare against Python output

From repo root (with `pip install -e .`):

```bash
python scripts/print_policy_decision_golden.py
python scripts/print_policy_decision_golden.py reshape
```

Not run in CI. You may see a **string difference only** on `timestamp` (e.g. `+00:00` vs `Z`)—same instant; TS tests assert the `Date.toISOString()` shape from [`policyDecisionToDict`](src/mcp/policy-decision-json.ts).

## Parity: what is *not* claimed

- Live `decide()` / `toolDecide()` parity (non-deterministic ids and timestamps from the engine).
- Full MCP tool-list parity, semantic bundle flows (TS arcane catalog still stubbed), swarm/gossip, full grimoire, HTTP/A2A depth.
- **DENY** or other `PolicyAction` variants unless a separate golden is added later.

To refresh a golden after an **intentional** serializer change, reproduce the fixed inputs from the corresponding test, re-run the serializer, and update the JSON (or change test + fixture together).

## Python oracle (reference modules)

- Cast wire shape: `vermyth/mcp/tools/casting/_legacy.py` — `cast_result_to_dict`
- Policy decision wire shape: `vermyth/mcp/tools/_serializers.py` — `policy_decision_to_dict`
