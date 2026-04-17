"""MCP tools for arcane compilation (inspect-only and bundle expansion)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.arcane.compiler import compile_ritual_spec
from vermyth.arcane.invoke import expand_to_invocation
from vermyth.arcane.types import RitualSpec

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [
    {
        "name": "expand_semantic_bundle",
        "description": "Expand a semantic bundle reference to skill_id + input + arcane_provenance (no execution).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
                "input": {"type": "object"},
            },
            "required": ["skill_id", "input"],
        },
    },
    {
        "name": "compile_ritual",
        "description": "Compile a RitualSpec JSON into a SemanticProgram with arcane metadata (returns program dict).",
        "inputSchema": {
            "type": "object",
            "properties": {"ritual": {"type": "object"}},
            "required": ["ritual"],
        },
    },
]


def tool_expand_semantic_bundle(
    tools: "VermythTools", *, skill_id: str, input: dict[str, Any]
) -> dict[str, Any]:
    _ = tools
    inv = expand_to_invocation(skill_id, input)
    return {
        "skill_id": inv.skill_id,
        "input": inv.input,
        "arcane_provenance": inv.arcane_provenance,
    }


def tool_compile_ritual(tools: "VermythTools", ritual: dict[str, Any]) -> dict[str, Any]:
    _ = tools
    spec = RitualSpec.model_validate(ritual)
    prog = compile_ritual_spec(spec)
    return {"program": prog.model_dump(mode="json")}


def dispatch_expand_semantic_bundle(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_expand_semantic_bundle(
        tools,
        skill_id=str(arguments.get("skill_id", "decide")),
        input=dict(arguments.get("input") or {}),
    )


def dispatch_compile_ritual(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_compile_ritual(tools, ritual=arguments.get("ritual", {}))


DISPATCH = {
    "expand_semantic_bundle": dispatch_expand_semantic_bundle,
    "compile_ritual": dispatch_compile_ritual,
}
