from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.engine.policy.registry import MODELS
from vermyth.registry import AspectRegistry
from vermyth.schema import Effect, Intent, PolicyThresholds, SemanticVector
from vermyth.mcp.tools._serializers import policy_decision_to_dict

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [
    {
        "name": "decide",
        "description": "Run a cast policy decision and return ALLOW/RESHAPE/DENY with rationale.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "object",
                    "properties": {
                        "objective": {"type": "string"},
                        "scope": {"type": "string"},
                        "reversibility": {
                            "type": "string",
                            "enum": ["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
                        },
                        "side_effect_tolerance": {
                            "type": "string",
                            "enum": ["NONE", "LOW", "MEDIUM", "HIGH"],
                        },
                    },
                    "required": [
                        "objective",
                        "scope",
                        "reversibility",
                        "side_effect_tolerance",
                    ],
                },
                "aspects": {"type": "array", "items": {"type": "string"}},
                "vector": {"type": "array", "items": {"type": "number"}},
                "parent_cast_id": {"type": "string"},
                "causal_root_cast_id": {"type": "string"},
                "thresholds": {"type": "object"},
                "effects": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Optional world-model effects (Effect) for effect-risk scoring.",
                },
                "policy_model": {
                    "type": "string",
                    "enum": ["rule_based", "threshold_tuned"],
                },
                "tuned_thresholds_path": {"type": "string"},
                "semantic_bundle": {
                    "type": "object",
                    "description": "Optional named bundle {bundle_id, version, params}; expanded before dispatch (MCP/HTTP /tools parity with /a2a/tasks).",
                },
            },
            "anyOf": [
                {"required": ["intent"]},
                {"required": ["semantic_bundle"]},
            ],
        },
    }
]


def _resolve_intent(arguments: dict[str, Any]) -> dict[str, Any]:
    intent_arg = arguments.get("intent")
    if isinstance(intent_arg, dict):
        return intent_arg
    return {
        "objective": arguments.get("objective", ""),
        "scope": arguments.get("scope", ""),
        "reversibility": arguments.get("reversibility", "PARTIAL"),
        "side_effect_tolerance": arguments.get("side_effect_tolerance", "MEDIUM"),
    }


def tool_decide(
    tools: "VermythTools",
    *,
    intent: dict[str, Any],
    aspects: list[str] | None = None,
    vector: list[float] | None = None,
    parent_cast_id: str | None = None,
    causal_root_cast_id: str | None = None,
    thresholds: dict[str, Any] | None = None,
    effects: list[dict[str, Any]] | None = None,
    policy_model: str | None = None,
    tuned_thresholds_path: str | None = None,
    __require_causal_root__: bool | None = None,
) -> dict[str, Any]:
    if __require_causal_root__ and not causal_root_cast_id:
        raise ValueError(
            "divination gate: causal_root_cast_id required when ritual/bundle requires causal context"
        )
    intent_obj = Intent.model_validate(intent)
    resolved_aspects = None
    if aspects is not None:
        registry = AspectRegistry.get()
        resolved = []
        for name in aspects:
            try:
                resolved.append(registry.resolve(name))
            except KeyError as exc:
                raise ValueError(f"Unknown aspect: {name}") from exc
        resolved_aspects = frozenset(resolved)
    vec_obj = (
        SemanticVector(components=tuple(float(x) for x in vector))
        if vector is not None
        else None
    )
    thresholds_obj = (
        PolicyThresholds.model_validate(thresholds) if thresholds is not None else None
    )
    effect_objs: list[Effect] | None = None
    if effects is not None:
        effect_objs = [Effect.model_validate(e) for e in effects]
    previous_model = tools._engine._policy_model
    try:
        if policy_model is not None:
            model_cls = MODELS.get(str(policy_model))
            if model_cls is None:
                raise ValueError(f"Unknown policy model: {policy_model}")
            if str(policy_model) == "threshold_tuned":
                tools._engine._policy_model = model_cls(thresholds_path=tuned_thresholds_path)
            else:
                tools._engine._policy_model = model_cls()
        decision, result = tools._engine.decide(
            intent_obj,
            aspects=resolved_aspects,
            vector=vec_obj,
            parent_cast_id=parent_cast_id,
            causal_root_cast_id=causal_root_cast_id,
            thresholds=thresholds_obj,
            grimoire=tools._grimoire,
            effects=effect_objs,
        )
    finally:
        tools._engine._policy_model = previous_model
    tools._grimoire.write(result)
    tools._grimoire.write_policy_decision(decision)
    return {
        "decision": policy_decision_to_dict(decision),
        "cast": tools._cast_result_to_dict(result),
    }


def dispatch_decide(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    args = dict(arguments)
    req = args.pop("__require_causal_root__", None)
    return tool_decide(
        tools,
        intent=_resolve_intent(args),
        aspects=args.get("aspects"),
        vector=args.get("vector"),
        parent_cast_id=args.get("parent_cast_id"),
        causal_root_cast_id=args.get("causal_root_cast_id"),
        thresholds=args.get("thresholds"),
        effects=args.get("effects"),
        policy_model=args.get("policy_model"),
        tuned_thresholds_path=args.get("tuned_thresholds_path"),
        __require_causal_root__=bool(req) if req is not None else None,
    )


DISPATCH = {"decide": dispatch_decide}
