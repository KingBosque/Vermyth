"""Expand protocol task inputs that carry semantic bundles (arcane ↔ boring runtime)."""

from __future__ import annotations

from typing import Any

from vermyth.arcane.constants import VERMYTH_EXT_SEMANTIC_BUNDLE
from vermyth.arcane.compiler import compile_semantic_bundle_ref
from vermyth.arcane.types import CompiledInvocation

# Meta-tools that consume bundle refs with their own argument shape; do not pre-expand.
_TOOL_INVOCATION_SKIP_SEMANTIC_EXPANSION: frozenset[str] = frozenset(
    {
        "expand_semantic_bundle",
        "compile_ritual",
    }
)


def extract_semantic_bundle_ref(inp: dict[str, Any]) -> dict[str, Any] | None:
    if "semantic_bundle" in inp:
        ref = inp["semantic_bundle"]
        return ref if isinstance(ref, dict) else None
    ext = inp.get("extensions")
    if isinstance(ext, dict):
        ref = ext.get(VERMYTH_EXT_SEMANTIC_BUNDLE)
        return ref if isinstance(ref, dict) else None
    return None


def strip_bundle_keys(inp: dict[str, Any]) -> dict[str, Any]:
    out = dict(inp)
    out.pop("semantic_bundle", None)
    ext = out.get("extensions")
    if isinstance(ext, dict) and VERMYTH_EXT_SEMANTIC_BUNDLE in ext:
        ext = {k: v for k, v in ext.items() if k != VERMYTH_EXT_SEMANTIC_BUNDLE}
        if ext:
            out["extensions"] = ext
        else:
            out.pop("extensions", None)
    return out


def expand_task_input(skill_id: str, inp: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """
    If input contains a semantic bundle reference, compile it and return
    (skill_id, merged_input, provenance). Otherwise return (skill_id, inp, None).
    """
    ref = extract_semantic_bundle_ref(inp)
    if not ref:
        return skill_id, inp, None
    inv = compile_semantic_bundle_ref(ref)
    base = strip_bundle_keys(inp)
    merged = {**base, **inv.input}
    return inv.skill_id, merged, inv.arcane_provenance


def expand_to_invocation(skill_id: str, inp: dict[str, Any]) -> CompiledInvocation:
    """Always returns an invocation; if no bundle, pass-through."""
    sid, merged, prov = expand_task_input(skill_id, inp)
    if prov is None:
        return CompiledInvocation(skill_id=sid, input=merged, arcane_provenance={})
    return CompiledInvocation(
        skill_id=sid,
        input=merged,
        arcane_provenance=prov,
    )


def resolve_tool_invocation(
    tool_name: str, arguments: dict[str, Any]
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """
    Resolve MCP/HTTP tool name + arguments using the same expansion as TaskGateway.

    When ``arguments`` contains a semantic bundle reference, returns the compiled
    tool name (skill id), merged arguments, and provenance. Otherwise returns
    ``(tool_name, arguments, None)`` unchanged.

    Meta-tools that consume bundle references with a non-task input shape are exempt.
    """
    if tool_name in _TOOL_INVOCATION_SKIP_SEMANTIC_EXPANSION:
        return tool_name, arguments, None
    return expand_task_input(tool_name, arguments)


def attach_arcane_provenance(
    result: Any, arcane_provenance: dict[str, Any] | None
) -> Any:
    """If provenance is set and the tool returned a dict, add ``arcane_provenance`` key."""
    if arcane_provenance is None:
        return result
    if isinstance(result, dict):
        out = dict(result)
        out["arcane_provenance"] = arcane_provenance
        return out
    return result
