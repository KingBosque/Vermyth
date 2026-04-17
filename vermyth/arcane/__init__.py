"""Arcane ontology compilation layer (maps to semantic IR + policy + programs)."""

from vermyth.arcane.compiler import (
    apply_banishment_to_program,
    compile_ritual_spec,
    compile_semantic_bundle_ref,
    merge_ward_into_thresholds,
)
from vermyth.arcane.discovery import (
    build_guided_upgrade,
    inspect_semantic_bundle_detail,
    list_bundle_catalog,
    list_bundle_ids,
    load_primary_bundle_manifest,
    preview_compiled_invocation,
)
from vermyth.arcane.recommend import recommend_for_plain_invocation
from vermyth.arcane.invoke import (
    attach_arcane_provenance,
    expand_task_input,
    expand_to_invocation,
    extract_semantic_bundle_ref,
    resolve_tool_invocation,
)
from vermyth.arcane.types import (
    BanishmentSpec,
    BundleRecommendationSpec,
    CompiledInvocation,
    DivinationSpec,
    RecommendationRule,
    RecommendationTier,
    RitualSpec,
    SemanticBundleManifest,
    WardSpec,
)

__all__ = [
    "BanishmentSpec",
    "BundleRecommendationSpec",
    "CompiledInvocation",
    "DivinationSpec",
    "RecommendationRule",
    "RecommendationTier",
    "RitualSpec",
    "SemanticBundleManifest",
    "WardSpec",
    "apply_banishment_to_program",
    "compile_ritual_spec",
    "compile_semantic_bundle_ref",
    "merge_ward_into_thresholds",
    "attach_arcane_provenance",
    "build_guided_upgrade",
    "expand_task_input",
    "expand_to_invocation",
    "extract_semantic_bundle_ref",
    "inspect_semantic_bundle_detail",
    "list_bundle_catalog",
    "list_bundle_ids",
    "load_primary_bundle_manifest",
    "preview_compiled_invocation",
    "recommend_for_plain_invocation",
    "resolve_tool_invocation",
]
