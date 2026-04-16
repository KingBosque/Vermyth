from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.registry import AspectRegistry
from vermyth.schema import ContradictionSeverity, EffectClass, RegisteredAspect, Sigil

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'register_aspect',
  'description': 'Register a new Aspect beyond the six canonical members.',
  'inputSchema': {'type': 'object',
                  'properties': {'aspect_id': {'type': 'string'},
                                 'polarity': {'type': 'integer', 'enum': [-1, 1]},
                                 'entropy_coefficient': {'type': 'number'},
                                 'symbol': {'type': 'string'}},
                  'required': ['aspect_id', 'polarity', 'entropy_coefficient', 'symbol']}},
 {'name': 'register_sigil',
  'description': 'Register a named Sigil for a specific aspect combination (optionally '
                 'overriding).',
  'inputSchema': {'type': 'object',
                  'properties': {'name': {'type': 'string'},
                                 'aspects': {'type': 'array', 'items': {'type': 'string'}},
                                 'effect_class': {'type': 'string'},
                                 'resonance_ceiling': {'type': 'number'},
                                 'contradiction_severity': {'type': 'string'},
                                 'allow_override': {'type': 'boolean'}},
                  'required': ['name',
                               'aspects',
                               'effect_class',
                               'resonance_ceiling',
                               'contradiction_severity']}},
 {'name': 'registered_aspects',
  'description': 'List registered Aspects (non-canonical).',
  'inputSchema': {'type': 'object', 'properties': {}, 'required': []}},
 {'name': 'registered_sigils',
  'description': 'List registered Sigils (overrides/extensions).',
  'inputSchema': {'type': 'object', 'properties': {}, 'required': []}}]



def tool_register_aspect(
    tools: "VermythTools", aspect_id: str, polarity: int, entropy_coefficient: float, symbol: str
) -> dict[str, Any]:
    aspect = RegisteredAspect(
        name=str(aspect_id),
        polarity=int(polarity),
        entropy_coefficient=float(entropy_coefficient),
        symbol=str(symbol),
    )
    registry = AspectRegistry.get()
    registry.register(aspect)
    ordinal = registry.dimensionality - 1
    tools._grimoire.write_registered_aspect(aspect, ordinal)
    return {
        "name": aspect.name,
        "polarity": aspect.polarity,
        "entropy_coefficient": aspect.entropy_coefficient,
        "symbol": aspect.symbol,
        "ordinal": ordinal,
    }


def tool_register_sigil(tools: "VermythTools", payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("name is required")
    aspects_in = payload.get("aspects")
    if not isinstance(aspects_in, list) or not aspects_in:
        raise ValueError("aspects must be a non-empty list of aspect names")
    registry = AspectRegistry.get()
    resolved = []
    for n in aspects_in:
        if not isinstance(n, str):
            raise ValueError("aspects must be a list of strings")
        try:
            resolved.append(registry.resolve(n))
        except KeyError as exc:
            raise ValueError(f"Unknown aspect: {n}") from exc
    aspects_fs = frozenset(resolved)
    effect_class = EffectClass[str(payload.get("effect_class", ""))]
    contradiction = ContradictionSeverity[str(payload.get("contradiction_severity", "NONE"))]
    ceiling = float(payload.get("resonance_ceiling", 1.0))
    allow_override = bool(payload.get("allow_override", False))

    sigil = Sigil(
        name=name,
        aspects=aspects_fs,
        effect_class=effect_class,
        resonance_ceiling=ceiling,
        contradiction_severity=contradiction,
    )
    entry = {
        "name": sigil.name,
        "aspects": [a.name for a in sigil.aspects],
        "effect_class": sigil.effect_class.name,
        "resonance_ceiling": sigil.resonance_ceiling,
    }
    if hasattr(tools._engine, "composition_engine") and hasattr(
        tools._engine.composition_engine, "register_sigil_entry"
    ):
        tools._engine.composition_engine.register_sigil_entry(
            aspects_fs, entry, allow_override=allow_override
        )
    else:
        raise RuntimeError("composition engine does not support register_sigil_entry")

    tools._grimoire.write_registered_sigil(
        name=sigil.name,
        aspects=[a.name for a in sigil.aspects],
        effect_class=sigil.effect_class.name,
        resonance_ceiling=sigil.resonance_ceiling,
        contradiction_severity=sigil.contradiction_severity.name,
        is_override=allow_override,
    )
    return {
        "name": sigil.name,
        "aspects": sorted(a.name for a in sigil.aspects),
        "effect_class": sigil.effect_class.name,
        "resonance_ceiling": sigil.resonance_ceiling,
        "contradiction_severity": sigil.contradiction_severity.name,
        "allow_override": allow_override,
    }


def tool_registered_aspects(tools: "VermythTools") -> list[dict[str, Any]]:
    reg = AspectRegistry.get()
    out: list[dict[str, Any]] = []
    for idx, a in enumerate(reg.full_order):
        if isinstance(a, RegisteredAspect):
            out.append(
                {
                    "name": a.name,
                    "polarity": a.polarity,
                    "entropy_coefficient": a.entropy_coefficient,
                    "symbol": a.symbol,
                    "ordinal": idx,
                }
            )
    return out


def tool_registered_sigils(tools: "VermythTools") -> list[dict[str, Any]]:
    return tools._grimoire.query_registered_sigils()


def dispatch_register_aspect(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_register_aspect(
        tools,
        aspect_id=arguments.get("aspect_id", ""),
        polarity=int(arguments.get("polarity", 1)),
        entropy_coefficient=float(arguments.get("entropy_coefficient", 0.0)),
        symbol=arguments.get("symbol", ""),
    )


def dispatch_register_sigil(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_register_sigil(tools, arguments)


def dispatch_registered_aspects(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    _ = arguments
    return tool_registered_aspects(tools)


def dispatch_registered_sigils(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    _ = arguments
    return tool_registered_sigils(tools)


DISPATCH = {
    "register_aspect": dispatch_register_aspect,
    "register_sigil": dispatch_register_sigil,
    "registered_aspects": dispatch_registered_aspects,
    "registered_sigils": dispatch_registered_sigils,
}
