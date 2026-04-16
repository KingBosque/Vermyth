from __future__ import annotations

from pathlib import Path

from vermyth.engine.composition import CompositionEngine
from vermyth.engine.projection_backends import ProjectionBackend, backend_from_env
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.tools import VermythTools
from vermyth.observability import EventBus
from vermyth.registry import AspectRegistry
from vermyth.schema import ContradictionSeverity, EffectClass, Sigil


def build_tools(
    db_path: Path | str | None = None,
    *,
    backend: ProjectionBackend | None = None,
) -> tuple[Grimoire, CompositionEngine, ResonanceEngine, VermythTools]:
    """
    Build a fully wired Vermyth stack: Grimoire + composition + resonance + tools.

    Loads registered aspects and registered sigil overrides from the grimoire and
    applies them to the runtime registry and composition table.
    """
    grimoire = Grimoire(db_path=db_path)
    registry = AspectRegistry.get()
    latest_basis = grimoire.read_latest_basis_version()

    for aspect, _ordinal in grimoire.query_registered_aspects():
        registry.register(aspect)
    registry.set_basis_version(latest_basis.version)

    composition = CompositionEngine()
    for row in grimoire.query_registered_sigils():
        aspects = [registry.resolve(n) for n in row["aspects"]]
        aspects_fs = frozenset(aspects)
        sigil = Sigil(
            name=row["name"],
            aspects=aspects_fs,
            effect_class=EffectClass[row["effect_class"]],
            resonance_ceiling=float(row["resonance_ceiling"]),
            contradiction_severity=ContradictionSeverity[row["contradiction_severity"]],
        )
        entry = {
            "name": sigil.name,
            "aspects": [a.name for a in sigil.aspects],
            "effect_class": sigil.effect_class.name,
            "resonance_ceiling": sigil.resonance_ceiling,
            "contradiction_severity": sigil.contradiction_severity.name,
        }
        composition.register_sigil_entry(
            aspects_fs, entry, allow_override=bool(row.get("is_override", False))
        )

    engine = ResonanceEngine(
        composition_engine=composition,
        backend=backend,
        contradictions=composition.contradictions,
    )
    tools = VermythTools(engine, grimoire, event_bus=EventBus())
    return grimoire, composition, engine, tools


def build_tools_from_env(
    db_path: Path | str | None = None,
) -> tuple[Grimoire, CompositionEngine, ResonanceEngine, VermythTools]:
    """
    Convenience entry point for CLI/MCP. Uses env-driven backend selection.

    See `vermyth.engine.projection_backends.backend_from_env`.
    """

    backend = backend_from_env()
    return build_tools(db_path, backend=backend)

