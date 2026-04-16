# ADR 0001: Vermyth as Semantic IR Runtime

## Status

Accepted

## Context

Vermyth currently ships language models, decision/runtime logic, MCP tooling, and experimental peer-coordination features in one repository. This made iteration fast, but it blurred the product boundary between:

- Internal semantic representation and control runtime.
- Tool/resource serving.
- Peer-agent protocol and transport.

Current ecosystem direction is converging on:

- MCP for tool/resource access.
- A2A-style envelopes for peer-agent collaboration.

Vermyth should preserve its strongest idea (semantic IR and explicit decision layer) while narrowing public promises.

## Decision

Vermyth is positioned as an internal semantic IR and decision-scoring runtime.

- Stable contract:
  - `vermyth.schema`
  - `vermyth.engine`
  - `vermyth.grimoire`
  - `vermyth.mcp` (tool/resource scope only)
  - `vermyth.cli`
- Experimental contract:
  - `vermyth.protocol.session_codec`
  - swarm/gossip federation paths
  - binary/geometric packet helpers
- External collaboration direction:
  - Keep MCP for tools/resources.
  - Add an A2A-shaped outer adapter for agent-to-agent task exchange.

## Stability tiers

- Stable: versioned with backward-compatibility expectations and default surface.
- Experimental: available for research, off by default where possible, and subject to breaking changes.
- Deferred: planned but not yet committed to implementation.

## Consequences

- Documentation and API language must stop implying custom federation as a public standard.
- MCP stays focused; peer-agent semantics move to a dedicated outer boundary.
- Experimental federation code remains available for research but is not part of the default contract.
