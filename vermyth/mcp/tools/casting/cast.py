from __future__ import annotations

from vermyth.mcp.tools.casting import _legacy

TOOL = _legacy.TOOLS[0]
tool_cast = _legacy.tool_cast
dispatch_cast = _legacy.dispatch_cast

__all__ = ["TOOL", "tool_cast", "dispatch_cast"]
