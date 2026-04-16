from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'crystallized_sigils',
  'description': 'List crystallized Sigils persisted in the grimoire (newest-first).',
  'inputSchema': {'type': 'object', 'properties': {}, 'required': []}},
 {'name': 'seeds',
  'description': 'List GlyphSeeds optionally filtered by crystallized status.',
  'inputSchema': {'type': 'object',
                  'properties': {'crystallized': {'type': 'boolean',
                                                  'description': 'Filter by crystallized status. '
                                                                 'Omit to return all seeds.'}},
                  'required': []}}]



def tool_crystallized_sigils(tools: "VermythTools") -> list[dict[str, Any]]:
    try:
        rows = tools._grimoire.query_crystallized_sigils()
        return [tools._crystallized_sigil_to_dict(row) for row in rows]
    except Exception as exc:
        raise RuntimeError(f"crystallized_sigils failed: {exc}") from exc


def tool_seeds(
    tools: "VermythTools",
    crystallized: Optional[bool],
) -> list[dict[str, Any]]:
    try:
        rows = tools._grimoire.query_seeds(
            aspect_pattern=None,
            crystallized=crystallized,
        )
        return [tools._seed_to_dict(seed) for seed in rows]
    except Exception as exc:
        raise RuntimeError(f"seeds failed: {exc}") from exc


def dispatch_crystallized_sigils(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    _ = arguments
    return tool_crystallized_sigils(tools)


def dispatch_seeds(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    return tool_seeds(tools, crystallized=arguments.get("crystallized"))


DISPATCH = {
    "crystallized_sigils": dispatch_crystallized_sigils,
    "seeds": dispatch_seeds,
}

