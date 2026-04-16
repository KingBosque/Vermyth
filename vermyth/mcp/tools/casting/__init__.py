from __future__ import annotations

from vermyth.mcp.tools.casting._legacy import cast_result_to_dict
from vermyth.mcp.tools.casting.auto_cast import TOOL as AUTO_CAST_TOOL
from vermyth.mcp.tools.casting.auto_cast import dispatch_auto_cast, tool_auto_cast
from vermyth.mcp.tools.casting.cast import TOOL as CAST_TOOL
from vermyth.mcp.tools.casting.cast import dispatch_cast, tool_cast
from vermyth.mcp.tools.casting.fluid_cast import TOOL as FLUID_CAST_TOOL
from vermyth.mcp.tools.casting.fluid_cast import dispatch_fluid_cast, tool_fluid_cast
from vermyth.mcp.tools.casting.geometric_cast import TOOL as GEOMETRIC_CAST_TOOL
from vermyth.mcp.tools.casting.geometric_cast import (
    dispatch_geometric_cast,
    tool_geometric_cast,
)

TOOLS = [
    CAST_TOOL,
    FLUID_CAST_TOOL,
    AUTO_CAST_TOOL,
    GEOMETRIC_CAST_TOOL,
]

DISPATCH = {
    "cast": dispatch_cast,
    "fluid_cast": dispatch_fluid_cast,
    "auto_cast": dispatch_auto_cast,
    "geometric_cast": dispatch_geometric_cast,
}

__all__ = [
    "TOOLS",
    "DISPATCH",
    "cast_result_to_dict",
    "tool_cast",
    "tool_fluid_cast",
    "tool_auto_cast",
    "tool_geometric_cast",
    "dispatch_cast",
    "dispatch_fluid_cast",
    "dispatch_auto_cast",
    "dispatch_geometric_cast",
]
