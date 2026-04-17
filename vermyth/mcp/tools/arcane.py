"""MCP tools for arcane compilation (inspect-only and bundle expansion)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.arcane.compiler import compile_ritual_spec
from vermyth.arcane.discovery import inspect_semantic_bundle_detail, list_bundle_catalog
from vermyth.arcane.invoke import expand_to_invocation
from vermyth.arcane.recommend import recommend_for_plain_invocation
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
    {
        "name": "list_semantic_bundles",
        "description": "List available semantic bundles (built-in and VERMYTH_ARCANE_BUNDLE_DIR) with summaries and target_skill. Catalog rows may include a compact recommendation hint when the manifest declares recommendation tiers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["decide", "cast", "compile_program"],
                    "description": "Optional filter by bundle kind.",
                },
            },
        },
    },
    {
        "name": "inspect_semantic_bundle",
        "description": "Return bundle manifest, compiled preview (skill_id + input), and a copy-paste semantic_bundle ref (no execution).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bundle_id": {"type": "string"},
                "version": {"type": "integer"},
                "params": {"type": "object", "description": "Optional; omit for placeholder preview."},
            },
            "required": ["bundle_id", "version"],
        },
    },
    {
        "name": "recommend_semantic_bundles",
        "description": "Advisory: suggest semantic bundles for plain skill_id + input using manifest-declared recommendation tiers (inspectable matched_features; no execution).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
                "input": {"type": "object"},
                "min_strength": {
                    "type": "number",
                    "description": "Optional floor 0..1 for suggestions (default 0.55).",
                },
            },
            "required": ["skill_id", "input"],
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


def tool_list_semantic_bundles(
    tools: "VermythTools",
    *,
    kind: str | None = None,
) -> dict[str, Any]:
    _ = tools
    k = kind if kind in ("decide", "cast", "compile_program") else None
    rows = list_bundle_catalog(kind=k)
    return {"bundles": rows}


def tool_inspect_semantic_bundle(
    tools: "VermythTools",
    *,
    bundle_id: str,
    version: int,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = tools
    return inspect_semantic_bundle_detail(bundle_id, int(version), params=params)


def dispatch_list_semantic_bundles(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    raw = arguments.get("kind")
    k = str(raw) if raw is not None else None
    return tool_list_semantic_bundles(tools, kind=k)


def dispatch_inspect_semantic_bundle(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_inspect_semantic_bundle(
        tools,
        bundle_id=str(arguments.get("bundle_id", "")),
        version=int(arguments.get("version", 1)),
        params=dict(arguments["params"]) if isinstance(arguments.get("params"), dict) else None,
    )


def tool_recommend_semantic_bundles(
    tools: "VermythTools",
    *,
    skill_id: str,
    input: dict[str, Any],
    min_strength: float | None = None,
) -> dict[str, Any]:
    _ = tools
    if min_strength is not None:
        return recommend_for_plain_invocation(
            skill_id, input, min_strength=float(min_strength)
        )
    return recommend_for_plain_invocation(skill_id, input)


def dispatch_recommend_semantic_bundles(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    ms = arguments.get("min_strength")
    return tool_recommend_semantic_bundles(
        tools,
        skill_id=str(arguments.get("skill_id", "decide")),
        input=dict(arguments.get("input") or {}),
        min_strength=float(ms) if ms is not None else None,
    )


DISPATCH = {
    "expand_semantic_bundle": dispatch_expand_semantic_bundle,
    "compile_ritual": dispatch_compile_ritual,
    "list_semantic_bundles": dispatch_list_semantic_bundles,
    "inspect_semantic_bundle": dispatch_inspect_semantic_bundle,
    "recommend_semantic_bundles": dispatch_recommend_semantic_bundles,
}
