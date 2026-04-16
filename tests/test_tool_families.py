from __future__ import annotations

from vermyth.mcp.tool_definitions import TOOL_DEFINITIONS
from vermyth.mcp.tools import casting
from vermyth.mcp.tools import causal
from vermyth.mcp.tools import decisions
from vermyth.mcp.tools import drift
from vermyth.mcp.tools import genesis
from vermyth.mcp.tools import observability
from vermyth.mcp.tools import programs
from vermyth.mcp.tools import query
from vermyth.mcp.tools import registry
from vermyth.mcp.tools import seeds
from vermyth.mcp.tools import swarm


FAMILY_MODULES = [
    decisions,
    observability,
    casting,
    query,
    seeds,
    registry,
    drift,
    swarm,
    programs,
    genesis,
    causal,
]


def test_tool_families_have_matching_tools_and_dispatch() -> None:
    for module in FAMILY_MODULES:
        assert len(module.TOOLS) == len(module.DISPATCH)
        tool_names = {tool["name"] for tool in module.TOOLS}
        dispatch_names = set(module.DISPATCH.keys())
        assert tool_names == dispatch_names


def test_tool_definitions_stable_count() -> None:
    expected = sum(len(module.TOOLS) for module in FAMILY_MODULES)
    assert len(TOOL_DEFINITIONS) == expected == 42
