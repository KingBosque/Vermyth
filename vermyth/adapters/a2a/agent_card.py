from __future__ import annotations

from vermyth.adapters.a2a.types import AgentCard, AgentSkill


def build_agent_card(tool_definitions: list[dict]) -> AgentCard:
    skills: list[AgentSkill] = []
    for tool in tool_definitions:
        skills.append(
            AgentSkill(
                id=str(tool.get("name", "")),
                name=str(tool.get("name", "")),
                description=str(tool.get("description", "")),
            )
        )
    return AgentCard(
        name="vermyth",
        version="0.1.0",
        description="Semantic IR runtime with MCP tool surface.",
        skills=skills,
    )

