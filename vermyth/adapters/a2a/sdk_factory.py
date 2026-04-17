"""Build A2A Starlette app and AgentCard using a2a-sdk (optional [a2a] extra)."""

from __future__ import annotations

import os
from typing import Any

from vermyth.adapters.a2a.extensions import VERMYTH_EXTENSION_DECLARATIONS
from vermyth.adapters.a2a.vermyth_executor import VermythAgentExecutor


def build_sdk_agent_card(
    *,
    agent_url: str,
    tool_definitions: list[dict[str, Any]],
    protocol_version: str = "1.0.0",
) -> Any:
    from a2a.types import (
        AgentCapabilities,
        AgentCard,
        AgentExtension,
        AgentProvider,
        AgentSkill,
        HTTPAuthSecurityScheme,
    )

    skills = [
        AgentSkill(
            id=str(t.get("name", "")),
            name=str(t.get("name", "")),
            description=str(t.get("description", ""))[:2000],
            tags=["vermyth", "semantic-ir"],
        )
        for t in tool_definitions
        if t.get("name")
    ]
    extensions = [
        AgentExtension(
            uri=str(e["uri"]),
            description=e.get("description"),
            required=bool(e.get("required")),
        )
        for e in VERMYTH_EXTENSION_DECLARATIONS
    ]
    caps = AgentCapabilities(
        extensions=extensions,
        streaming=False,
        push_notifications=False,
        state_transition_history=True,
    )
    security_schemes = None
    security = None
    if os.environ.get("VERMYTH_HTTP_TOKEN") or os.environ.get("VERMYTH_A2A_REQUIRE_BEARER", "0") == "1":
        security_schemes = {
            "bearerAuth": HTTPAuthSecurityScheme(
                scheme="Bearer",
                bearer_format="JWT",
                description="Bearer token (set VERMYTH_HTTP_TOKEN for dev; production: OAuth2/JWT).",
            )
        }
        security = [{"bearerAuth": []}]
    org = os.environ.get("VERMYTH_AGENT_ORG", "Vermyth")
    doc_url = os.environ.get("VERMYTH_AGENT_DOC_URL", "https://github.com/")
    provider = AgentProvider(organization=org, url=doc_url)
    return AgentCard(
        name=os.environ.get("VERMYTH_AGENT_NAME", "vermyth"),
        description=os.environ.get(
            "VERMYTH_AGENT_DESCRIPTION",
            "Semantic IR and decision runtime (Vermyth). Skills map to MCP tools.",
        ),
        version=os.environ.get("VERMYTH_AGENT_VERSION", "0.1.0"),
        protocol_version=protocol_version,
        url=agent_url,
        preferred_transport="JSONRPC",
        capabilities=caps,
        skills=skills,
        default_input_modes=["application/json", "text/plain"],
        default_output_modes=["application/json"],
        provider=provider,
        security=security,
        security_schemes=security_schemes,
        supports_authenticated_extended_card=bool(
            os.environ.get("VERMYTH_EXTENDED_AGENT_CARD", "0") == "1"
        ),
        documentation_url=os.environ.get("VERMYTH_DOCUMENTATION_URL"),
    )


def build_a2a_starlette_app(
    *,
    tools: object,
    tool_dispatch: dict[str, Any],
    tool_definitions: list[dict[str, Any]],
    agent_base_url: str | None = None,
) -> Any:
    from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
    from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
    from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore

    base = agent_base_url or os.environ.get(
        "VERMYTH_A2A_PUBLIC_URL", "http://127.0.0.1:7788"
    )
    if not str(base).startswith(("http://", "https://")):
        base = f"http://{base}"
    card = build_sdk_agent_card(agent_url=str(base).rstrip("/") + "/", tool_definitions=tool_definitions)
    extended = None
    if card.supports_authenticated_extended_card:
        extended = build_sdk_agent_card(
            agent_url=str(base).rstrip("/") + "/", tool_definitions=tool_definitions
        )

    executor = VermythAgentExecutor(tools=tools, tool_dispatch=tool_dispatch)
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=card,
        http_handler=handler,
        extended_agent_card=extended,
    ).build()
