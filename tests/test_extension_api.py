import pytest
from pathlib import Path

from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.tools import VermythTools
from vermyth.registry import AspectRegistry



def _make_tools(tmp_path) -> VermythTools:
    g = Grimoire(db_path=tmp_path / "ext.db")
    eng = ResonanceEngine(CompositionEngine(), None)
    return VermythTools(eng, g)


def test_register_aspect_persists_and_expands_dimensionality(tmp_path: Path):
    tools = _make_tools(tmp_path)
    out = tools.tool_register_aspect(
        aspect_id="FIRE",
        polarity=1,
        entropy_coefficient=0.5,
        symbol="🔥",
    )
    assert out["name"] == "FIRE"
    assert AspectRegistry.get().dimensionality == 7

    g2 = Grimoire(db_path=tmp_path / "ext.db")
    AspectRegistry.reset()
    for aspect, _ordinal in g2.query_registered_aspects():
        AspectRegistry.get().register(aspect)
    assert AspectRegistry.get().dimensionality == 7


def test_register_sigil_override_requires_flag(tmp_path: Path):
    tools = _make_tools(tmp_path)
    payload = {
        "name": "MyOverride",
        "aspects": ["MIND", "LIGHT"],
        "effect_class": "REVELATION",
        "resonance_ceiling": 0.9,
        "contradiction_severity": "NONE",
    }
    with pytest.raises(ValueError):
        tools.tool_register_sigil(payload)

    ok = dict(payload)
    ok["allow_override"] = True
    tools.tool_register_sigil(ok)

    cast = tools.tool_cast(
        aspects=["MIND", "LIGHT"],
        intent={
            "objective": "study",
            "scope": "local",
            "reversibility": "REVERSIBLE",
            "side_effect_tolerance": "HIGH",
        },
    )
    assert cast["sigil_name"] == "MyOverride"

