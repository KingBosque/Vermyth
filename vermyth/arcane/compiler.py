"""Compile arcane constructs into plain runtime types (policy, programs, tool args)."""

from __future__ import annotations

import copy
from typing import Any

from vermyth.arcane.bundles import load_bundle
from vermyth.arcane.types import (
    BanishmentSpec,
    CompiledInvocation,
    DivinationSpec,
    RitualSpec,
    SemanticBundleManifest,
    WardSpec,
)
from vermyth.schema import CastNode, PolicyThresholds, RollbackStrategy, SemanticProgram


def merge_ward_into_thresholds(base: PolicyThresholds, ward: WardSpec) -> PolicyThresholds:
    d = base.model_dump(mode="json")
    if ward.allow_min_resonance is not None:
        d["allow_min_resonance"] = max(
            float(d["allow_min_resonance"]), float(ward.allow_min_resonance)
        )
    if ward.reshape_min_resonance is not None:
        d["reshape_min_resonance"] = max(
            float(d["reshape_min_resonance"]), float(ward.reshape_min_resonance)
        )
    if ward.max_drift_status is not None:
        d["max_drift_status"] = ward.max_drift_status.value
    if ward.effect_risk_min_score is not None:
        prev = d.get("effect_risk_min_score")
        d["effect_risk_min_score"] = (
            max(float(prev), float(ward.effect_risk_min_score))
            if prev is not None
            else float(ward.effect_risk_min_score)
        )
    if ward.scorer_weights is not None:
        sw = dict(d.get("scorer_weights") or {})
        sw.update(ward.scorer_weights)
        d["scorer_weights"] = sw
    return PolicyThresholds.model_validate(d)


def apply_divination_thresholds(
    base: PolicyThresholds, div: DivinationSpec
) -> PolicyThresholds:
    if div.thresholds is None:
        return base
    return merge_ward_into_thresholds(base, div.thresholds)


def apply_banishment_to_program(program: SemanticProgram, ban: BanishmentSpec) -> SemanticProgram:
    """Set default rollback on destructive-effect nodes when banishment is strict."""
    if not ban.strict:
        return program
    new_nodes: list[CastNode] = []
    for node in program.nodes:
        n = node
        if node.effects:
            needs = any(
                e.effect_type in ban.quarantine_effect_types for e in node.effects
            )
            if needs and node.rollback in (None, RollbackStrategy.NONE):
                n = node.model_copy(update={"rollback": ban.default_rollback})
        new_nodes.append(n)
    return program.model_copy(update={"nodes": new_nodes})


def compile_ritual_spec(spec: RitualSpec) -> SemanticProgram:
    """Attach arcane metadata and optional banishment to a semantic program."""
    prog = spec.program
    meta = dict(prog.metadata)
    meta["arcane"] = {
        "kind": "ritual",
        "ritual_id": spec.ritual_id,
        "ward": spec.ward.model_dump(mode="json") if spec.ward else None,
        "divination": spec.divination.model_dump(mode="json") if spec.divination else None,
        "banishment": spec.banishment.model_dump(mode="json") if spec.banishment else None,
    }
    meta["ritual"] = {"ritual_id": spec.ritual_id}
    prog = prog.model_copy(update={"metadata": meta, "name": prog.name or spec.ritual_id})
    if spec.banishment:
        prog = apply_banishment_to_program(prog, spec.banishment)
    return prog


def _format_template(obj: Any, params: dict[str, Any]) -> Any:
    if isinstance(obj, str):
        try:
            return obj.format(**params)
        except KeyError:
            return obj
    if isinstance(obj, dict):
        return {k: _format_template(v, params) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_format_template(v, params) for v in obj]
    return obj


def compile_manifest(
    manifest: SemanticBundleManifest, params: dict[str, Any]
) -> CompiledInvocation:
    body = _format_template(copy.deepcopy(manifest.template), params)
    prov: dict[str, Any] = {
        "bundle_id": manifest.id,
        "bundle_version": manifest.version,
        "kind": manifest.kind,
    }
    if manifest.kind == "decide":
        inp = dict(body)
        div = inp.pop("_divination", None)
        if isinstance(div, dict) and div.get("require_causal_context"):
            inp["__require_causal_root__"] = True
        if isinstance(div, dict) and div.get("thresholds"):
            base = PolicyThresholds.model_validate(inp.get("thresholds") or {})
            w = WardSpec.model_validate(div["thresholds"])
            inp["thresholds"] = merge_ward_into_thresholds(base, w).model_dump(mode="json")
        return CompiledInvocation(skill_id="decide", input=inp, arcane_provenance=prov)
    if manifest.kind == "cast":
        return CompiledInvocation(skill_id="cast", input=dict(body), arcane_provenance=prov)
    if manifest.kind == "compile_program":
        return CompiledInvocation(skill_id="compile_program", input=dict(body), arcane_provenance=prov)
    raise ValueError(f"unknown bundle kind: {manifest.kind}")


def compile_semantic_bundle_ref(bundle_ref: dict[str, Any]) -> CompiledInvocation:
    bid = str(bundle_ref["bundle_id"])
    ver = int(bundle_ref["version"])
    params = dict(bundle_ref.get("params") or {})
    manifest = load_bundle(bid, ver)
    missing = [k for k in manifest.param_keys if k not in params]
    if missing:
        raise ValueError(f"bundle {bid} missing params: {missing}")
    return compile_manifest(manifest, params)
