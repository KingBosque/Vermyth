"""Manifest-driven, conservative semantic-bundle recommendations for plain invocations."""

from __future__ import annotations

from typing import Any, Callable, Literal

from vermyth.arcane.discovery import (
    build_guided_upgrade,
    list_bundle_ids,
    load_primary_bundle_manifest,
)
from vermyth.arcane.invoke import extract_semantic_bundle_ref
from vermyth.arcane.types import (
    BundleRecommendationSpec,
    RecommendationRule,
    SemanticBundleManifest,
)

MatchKind = Literal["exact", "strong", "advisory"]


def _norm_aspects(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x).strip().upper() for x in raw]


def _intent_slice(arguments: dict[str, Any]) -> dict[str, Any]:
    intent = arguments.get("intent")
    if isinstance(intent, dict):
        return dict(intent)
    # Flat tool schema (e.g. cast): intent fields at top level
    out: dict[str, Any] = {}
    for k in ("objective", "scope", "reversibility", "side_effect_tolerance"):
        if k in arguments:
            out[k] = arguments[k]
    return out


def _intent_subset_eq(intent: dict[str, Any], required: dict[str, Any]) -> bool:
    for k, v in required.items():
        if intent.get(k) != v:
            return False
    return True


def _thresholds_eq(th: Any, required: dict[str, Any]) -> bool:
    if not isinstance(th, dict):
        return False
    try:
        for k, v in required.items():
            if float(th.get(k)) != float(v):
                return False
        return True
    except (TypeError, ValueError):
        return False


def _objective(arguments: dict[str, Any]) -> str:
    return str(_intent_slice(arguments).get("objective", ""))


def _eval_rule(rule: RecommendationRule, arguments: dict[str, Any]) -> bool:
    op = rule.op
    fn = RULE_OPS.get(op)
    if fn is None:
        return False
    return fn(rule, arguments)


# --- Declarative ops (referenced by manifest recommendation.tiers[].require_all[].op) ---


def _op_aspects_eq(rule: RecommendationRule, arguments: dict[str, Any]) -> bool:
    val = rule.value
    if not isinstance(val, list):
        return False
    return _norm_aspects(arguments.get("aspects")) == [str(x).upper() for x in val]


def _op_intent_subset_eq(rule: RecommendationRule, arguments: dict[str, Any]) -> bool:
    val = rule.value
    if not isinstance(val, dict):
        return False
    return _intent_subset_eq(_intent_slice(arguments), val)


def _op_thresholds_eq(rule: RecommendationRule, arguments: dict[str, Any]) -> bool:
    val = rule.value
    if not isinstance(val, dict):
        return False
    return _thresholds_eq(arguments.get("thresholds"), val)


def _op_objective_starts_with(rule: RecommendationRule, arguments: dict[str, Any]) -> bool:
    prefix = str(rule.value or "")
    obj = _objective(arguments)
    ok = obj.startswith(prefix)
    return (not ok) if rule.negate else ok


def _op_objective_length_between(rule: RecommendationRule, arguments: dict[str, Any]) -> bool:
    obj = _objective(arguments)
    if not obj.strip():
        return False
    ln = len(obj)
    if rule.min_len is not None and ln < rule.min_len:
        return False
    if rule.max_len is not None and ln > rule.max_len:
        return False
    return True


def _op_field_eq(rule: RecommendationRule, arguments: dict[str, Any]) -> bool:
    path = rule.path or ""
    if not path or path not in arguments:
        return False
    return arguments.get(path) == rule.value


def _op_field_present(rule: RecommendationRule, arguments: dict[str, Any]) -> bool:
    path = rule.path or ""
    if not path:
        return False
    v = arguments.get(path)
    return bool(v)


RULE_OPS: dict[str, Callable[[RecommendationRule, dict[str, Any]], bool]] = {
    "aspects_eq": _op_aspects_eq,
    "intent_subset_eq": _op_intent_subset_eq,
    "thresholds_eq": _op_thresholds_eq,
    "objective_starts_with": _op_objective_starts_with,
    "objective_length_between": _op_objective_length_between,
    "field_eq": _op_field_eq,
    "field_present": _op_field_present,
}


def _matched_feature_tags(rule: RecommendationRule, arguments: dict[str, Any]) -> list[str]:
    rid = rule.rule_id
    base = f"rule:{rule.op}"
    if rid:
        return [f"{base}:{rid}"]
    return [base]


def _evaluate_bundle(
    manifest: SemanticBundleManifest,
    skill_id: str,
    arguments: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return 0 or 1 recommendation row for this manifest."""
    spec: BundleRecommendationSpec | None = manifest.recommendation
    if spec is None:
        return []
    if skill_id not in spec.target_skills:
        return []
    target_skill = manifest.kind

    for tier in spec.tiers:
        matched: list[str] = []
        ok = True
        for rule in tier.require_all:
            if not _eval_rule(rule, arguments):
                ok = False
                break
            matched.extend(_matched_feature_tags(rule, arguments))
        if not ok:
            continue
        matched.append(f"tier:{tier.match_kind}")
        matched.append(f"bundle:{manifest.id}")
        return [
            {
                "bundle_id": manifest.id,
                "version": manifest.version,
                "strength": float(tier.strength),
                "match_kind": tier.match_kind,
                "matched_features": matched,
                "target_skill": target_skill,
                "why_better": spec.why_better,
                "guided_upgrade": build_guided_upgrade(manifest),
            }
        ]
    return []


def recommend_for_plain_invocation(
    skill_id: str,
    arguments: dict[str, Any],
    *,
    min_strength: float = 0.55,
    surface: str | None = None,
    emit_recommendation_telemetry: bool = True,
) -> dict[str, Any]:
    """
    Evaluate plain tool arguments (no semantic_bundle) using manifest ``recommendation`` tiers.

    Advisory only; does not execute tools or rewrite requests.

    When local bundle telemetry is enabled (``VERMYTH_BUNDLE_TELEMETRY``), optional
    ``surface`` (e.g. ``mcp``, ``http``) tags recommendation events. Set
    ``emit_recommendation_telemetry=False`` when calling internally for missed-upgrade
    detection to avoid double-counting recommendation events.
    """
    if extract_semantic_bundle_ref(arguments):
        return {
            "skill_id": skill_id,
            "recommendations": [],
            "note": "input already contains semantic_bundle; nothing to suggest",
        }

    out: list[dict[str, Any]] = []
    for bid in list_bundle_ids():
        m = load_primary_bundle_manifest(bid)
        out.extend(_evaluate_bundle(m, skill_id, arguments))

    out = [r for r in out if float(r["strength"]) >= min_strength]
    out.sort(key=lambda r: (-float(r["strength"]), r["bundle_id"]))
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in out:
        bid = str(r["bundle_id"])
        if bid in seen:
            continue
        seen.add(bid)
        deduped.append(r)

    if emit_recommendation_telemetry and surface and deduped:
        from vermyth.arcane.bundle_telemetry import is_enabled, record_bundle_recommended

        if is_enabled():
            surf = surface
            for r in deduped:
                record_bundle_recommended(
                    surface=surf,
                    skill_id=skill_id,
                    bundle_id=str(r["bundle_id"]),
                    version=int(r["version"]),
                    strength=float(r["strength"]),
                    match_kind=str(r["match_kind"]),
                    target_skill=str(r["target_skill"]),
                )

    return {
        "skill_id": skill_id,
        "recommendations": deduped,
        "advisory": True,
        "note": "Recommendations are manifest-driven and inspectable; verify with inspect_semantic_bundle before adopting",
    }


__all__ = ["RULE_OPS", "recommend_for_plain_invocation"]
