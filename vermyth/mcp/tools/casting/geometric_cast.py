from __future__ import annotations

from vermyth.mcp.tools.casting import _legacy

TOOL = _legacy.TOOLS[3]
tool_geometric_cast = _legacy.tool_geometric_cast
dispatch_geometric_cast = _legacy.dispatch_geometric_cast

__all__ = ["TOOL", "tool_geometric_cast", "dispatch_geometric_cast"]
