from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [
    {
        "name": "events_tail",
        "description": "Read recent observability events emitted by Vermyth.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer"},
                "event_type": {"type": "string"},
            },
            "required": [],
        },
    }
]


def tool_events_tail(
    tools: "VermythTools", *, n: int = 100, event_type: str | None = None
) -> list[dict[str, Any]]:
    return tools.tool_events_tail(n=int(n), event_type=event_type)


def dispatch_events_tail(tools: "VermythTools", arguments: dict[str, Any]) -> list[dict[str, Any]]:
    return tool_events_tail(
        tools,
        n=int(arguments.get("n", 100)),
        event_type=arguments.get("event_type"),
    )


DISPATCH = {"events_tail": dispatch_events_tail}
