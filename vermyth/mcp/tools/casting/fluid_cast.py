from __future__ import annotations

from vermyth.mcp.tools.casting import _legacy

TOOL = _legacy.TOOLS[1]
tool_fluid_cast = _legacy.tool_fluid_cast
dispatch_fluid_cast = _legacy.dispatch_fluid_cast

__all__ = ["TOOL", "tool_fluid_cast", "dispatch_fluid_cast"]
