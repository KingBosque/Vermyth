"""Arcane ontology compilation layer (maps to semantic IR + policy + programs)."""

from vermyth.arcane.compiler import (
    apply_banishment_to_program,
    compile_ritual_spec,
    compile_semantic_bundle_ref,
    merge_ward_into_thresholds,
)
from vermyth.arcane.discovery import (
    inspect_semantic_bundle_detail,
    list_bundle_catalog,
    list_bundle_ids,
    preview_compiled_invocation,
)
from vermyth.arcane.invoke import (
    attach_arcane_provenance,
    expand_task_input,
    expand_to_invocation,
    extract_semantic_bundle_ref,
    resolve_tool_invocation,
)
from vermyth.arcane.types import (
    BanishmentSpec,
    CompiledInvocation,
    DivinationSpec,
    RitualSpec,
    SemanticBundleManifest,
    WardSpec,
)

__all__ = [
    "BanishmentSpec",
    "CompiledInvocation",
    "DivinationSpec",
    "RitualSpec",
    "SemanticBundleManifest",
    "WardSpec",
    "apply_banishment_to_program",
    "compile_ritual_spec",
    "compile_semantic_bundle_ref",
    "merge_ward_into_thresholds",
    "attach_arcane_provenance",
    "expand_task_input",
    "expand_to_invocation",
    "extract_semantic_bundle_ref",
    "inspect_semantic_bundle_detail",
    "list_bundle_catalog",
    "list_bundle_ids",
    "preview_compiled_invocation",
    "resolve_tool_invocation",
]
