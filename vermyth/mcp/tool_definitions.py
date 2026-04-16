from __future__ import annotations

from vermyth.mcp.tools import casting as casting_tools
from vermyth.mcp.tools import causal as causal_tools
from vermyth.mcp.tools import decisions as decision_tools
from vermyth.mcp.tools import drift as drift_tools
from vermyth.mcp.tools import genesis as genesis_tools
from vermyth.mcp.tools import programs as program_tools
from vermyth.mcp.tools import query as query_tools
from vermyth.mcp.tools import registry as registry_tools
from vermyth.mcp.tools import seeds as seed_tools
from vermyth.mcp.tools import swarm as swarm_tools
from vermyth.mcp.tools import observability as observability_tools

TOOL_DEFINITIONS = [
    *decision_tools.TOOLS,
    *observability_tools.TOOLS,
    *casting_tools.TOOLS,
    *query_tools.TOOLS,
    *seed_tools.TOOLS,
    *registry_tools.TOOLS,
    *drift_tools.TOOLS,
    *swarm_tools.TOOLS,
    *program_tools.TOOLS,
    *genesis_tools.TOOLS,
    *causal_tools.TOOLS,
]
