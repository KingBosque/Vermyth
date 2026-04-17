"""Read-only discovery for semantic bundles (listing, catalog, compiled preview)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from vermyth.arcane.bundles import _bundles_dir, env_bundle_dir, load_bundle
from vermyth.arcane.compiler import compile_semantic_bundle_ref
from vermyth.arcane.types import SemanticBundleManifest


def target_skill_for_kind(kind: Literal["decide", "cast", "compile_program"]) -> str:
    """Skill name after expansion; matches compile_manifest."""
    return kind


def placeholder_params(param_keys: tuple[str, ...]) -> dict[str, str]:
    """Synthetic params for preview when callers omit explicit params."""
    return {k: f"<{k}>" for k in param_keys}


def build_guided_upgrade(manifest: SemanticBundleManifest) -> dict[str, Any]:
    """
    Additive, copy-paste friendly path from recommendation or inspect to invocation.

    Does not execute tools or mutate caller payloads.
    """
    bid = manifest.id
    ver = manifest.version
    params = placeholder_params(manifest.param_keys)
    ref = {"bundle_id": bid, "version": ver, "params": params}
    return {
        "semantic_bundle": ref,
        "inspect": {
            "mcp_tool": "inspect_semantic_bundle",
            "mcp_arguments": {"bundle_id": bid, "version": ver},
            "http_get_path": f"/arcane/bundles/{bid}?version={ver}",
            "mcp_resource_uri": f"vermyth://semantic_bundle/{bid}?version={ver}",
        },
        "invoke": {
            "target_skill": target_skill_for_kind(manifest.kind),
            "pattern": (
                "Pass semantic_bundle alongside other fields on task input or tool arguments; "
                "the server expands before dispatch (same as MCP/HTTP parity paths)."
            ),
        },
    }


def _primary_bundle_path(bundle_id: str) -> Path | None:
    """Package path wins over VERMYTH_ARCANE_BUNDLE_DIR (same as load_bundle)."""
    p = _bundles_dir() / f"{bundle_id}.json"
    if p.is_file():
        return p
    extra = env_bundle_dir()
    if extra:
        e = extra / f"{bundle_id}.json"
        if e.is_file():
            return e
    return None


def list_bundle_ids() -> list[str]:
    """All bundle ids from package data and optional overlay directory."""
    stems: set[str] = set()
    for base in (_bundles_dir(), env_bundle_dir()):
        if base and base.is_dir():
            stems.update(p.stem for p in base.glob("*.json"))
    return sorted(stems)


def _load_manifest_for_bundle(bundle_id: str) -> SemanticBundleManifest:
    path = _primary_bundle_path(bundle_id)
    if path is None:
        raise FileNotFoundError(f"semantic bundle not found: {bundle_id}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    ver = int(raw["version"])
    return load_bundle(bundle_id, ver)


def load_primary_bundle_manifest(bundle_id: str) -> SemanticBundleManifest:
    """Load manifest from the primary bundle JSON path (same resolution as catalog)."""
    return _load_manifest_for_bundle(bundle_id)


def _recommendation_catalog_hint(manifest: SemanticBundleManifest) -> dict[str, Any] | None:
    spec = manifest.recommendation
    if spec is None:
        return None
    return {
        "target_skills": list(spec.target_skills),
        "tier_count": len(spec.tiers),
        "match_kinds": [t.match_kind for t in spec.tiers],
    }


def catalog_entry_dict(manifest: SemanticBundleManifest) -> dict[str, Any]:
    row: dict[str, Any] = {
        "bundle_id": manifest.id,
        "version": manifest.version,
        "kind": manifest.kind,
        "param_keys": list(manifest.param_keys),
        "summary": manifest.summary,
        "description": manifest.description,
        "recommended_for": list(manifest.recommended_for),
        "stability": manifest.stability or "stable",
        "target_skill": target_skill_for_kind(manifest.kind),
    }
    if manifest.library is not None:
        row["library"] = manifest.library
    hint = _recommendation_catalog_hint(manifest)
    if hint is not None:
        row["recommendation"] = hint
    return row


def list_bundle_catalog(
    *,
    kind: Literal["decide", "cast", "compile_program"] | None = None,
) -> list[dict[str, Any]]:
    """One catalog row per bundle id (primary path)."""
    rows: list[dict[str, Any]] = []
    for bid in list_bundle_ids():
        m = _load_manifest_for_bundle(bid)
        if kind is not None and m.kind != kind:
            continue
        rows.append(catalog_entry_dict(m))
    return rows


def preview_compiled_invocation(
    bundle_id: str,
    version: int,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compiled skill_id + input + provenance; no tool execution."""
    if params is None:
        m = load_bundle(bundle_id, version)
        params = placeholder_params(m.param_keys)
    ref: dict[str, Any] = {
        "bundle_id": bundle_id,
        "version": version,
        "params": params,
    }
    inv = compile_semantic_bundle_ref(ref)
    return {
        "skill_id": inv.skill_id,
        "input": inv.input,
        "arcane_provenance": inv.arcane_provenance,
    }


def inspect_semantic_bundle_detail(
    bundle_id: str,
    version: int,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Manifest (JSON-safe), compiled preview, and copy-paste semantic_bundle ref."""
    manifest = load_bundle(bundle_id, version)
    preview = preview_compiled_invocation(bundle_id, version, params=params)
    ref_example: dict[str, Any] = {
        "bundle_id": bundle_id,
        "version": version,
        "params": params
        if params is not None
        else placeholder_params(manifest.param_keys),
    }
    return {
        "manifest": manifest.model_dump(mode="json"),
        "compiled_preview": preview,
        "semantic_bundle_ref_example": ref_example,
        "guided_upgrade": build_guided_upgrade(manifest),
    }
