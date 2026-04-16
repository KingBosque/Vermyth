"""Crystallization closed-loop: persisted sigils, provenance, and generation reset."""

import io
import json
from pathlib import Path

import pytest

from vermyth.cli.main import VermythCLI
from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.server import VermythMCPServer
from vermyth.mcp.tools import VermythTools
from vermyth.schema import AspectID, SemanticVector


class _Backend:
    def project(self, objective: str, scope: str) -> list[float]:
        # Encode desired aspects in scope as e.g. "MIND+LIGHT"
        names = [p for p in scope.split("+") if p]
        aspects = frozenset(AspectID[n] for n in names)
        v = SemanticVector.from_aspects(aspects)
        return list(v.components)


def _intent(scope: str):
    return {
        "objective": "study the pattern",
        "scope": scope,
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "HIGH",
    }


@pytest.fixture
def tools(tmp_path):
    db = tmp_path / "grimoire.db"
    eng = ResonanceEngine(CompositionEngine(), backend=_Backend())
    g = Grimoire(db_path=db)
    return VermythTools(eng, g)


@pytest.fixture
def cli(tmp_path):
    db = tmp_path / "cli.db"
    eng = ResonanceEngine(CompositionEngine(), backend=_Backend())
    g = Grimoire(db_path=db)
    return VermythCLI(engine=eng, grimoire=g)


def _seed_for(tools: VermythTools, aspects: list[str]) -> dict:
    seeds = tools.tool_seeds(None)
    for s in seeds:
        if sorted(s["aspects"]) == sorted(aspects):
            return s
    raise AssertionError("seed not found")


def test_casts_crystallize_persisted_and_next_cast_uses_crystal(tools: VermythTools):
    aspects = ["LIGHT"]
    scope = "LIGHT"
    # Gen 1 thresholds: 10 casts
    for _ in range(10):
        tools.tool_cast(aspects=aspects, intent=_intent(scope))
    sigils = tools.tool_crystallized_sigils()
    assert len(sigils) >= 1
    crystal = sigils[0]
    assert crystal["generation"] == 1

    out = tools.tool_cast(aspects=aspects, intent=_intent(scope))
    prov = out["provenance"]
    assert prov is not None
    assert prov["source"] == "crystallized"
    assert prov["generation"] == 1
    assert prov["crystallized_sigil_name"]


def test_seed_resets_and_generation_increments_after_crystallize(tools: VermythTools):
    aspects = ["LIGHT"]
    scope = "LIGHT"
    for _ in range(10):
        tools.tool_cast(aspects=aspects, intent=_intent(scope))
    seed = _seed_for(tools, aspects)
    assert seed["generation"] == 2
    assert seed["observed_count"] == 0


def test_generation_2_requires_15_casts(tools: VermythTools):
    aspects = ["LIGHT"]
    scope = "LIGHT"
    for _ in range(10):
        tools.tool_cast(aspects=aspects, intent=_intent(scope))
    seed = _seed_for(tools, aspects)
    assert seed["generation"] == 2

    # 14 casts is not enough for gen2
    for _ in range(14):
        tools.tool_cast(aspects=aspects, intent=_intent(scope))
    sigils_before = tools.tool_crystallized_sigils()
    gen2_present = any(s.get("generation") == 2 for s in sigils_before)
    assert gen2_present is False

    tools.tool_cast(aspects=aspects, intent=_intent(scope))
    sigils_after = tools.tool_crystallized_sigils()
    assert any(s.get("generation") == 2 for s in sigils_after)


def test_cli_sigils_subcommand_prints_table(cli: VermythCLI, capsys):
    cli.run(
        [
            "cast",
            "--aspects",
            "LIGHT",
            "--objective",
            "x",
            "--scope",
            "LIGHT",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
        ]
    )
    capsys.readouterr()
    # force crystallization
    for _ in range(9):
        cli.run(
            [
                "cast",
                "--aspects",
                "LIGHT",
                "--objective",
                "x",
                "--scope",
                "LIGHT",
                "--reversibility",
                "REVERSIBLE",
                "--side-effect-tolerance",
                "HIGH",
            ]
        )
        capsys.readouterr()
    cli.run(["sigils"])
    out = capsys.readouterr().out
    assert "CRYSTALLIZED_AT" in out
    assert "Glyph:" in out


def test_mcp_tools_list_includes_crystallized_sigils(tmp_path):
    db = tmp_path / "mcp.db"
    eng = ResonanceEngine(CompositionEngine(), backend=None)
    g = Grimoire(db_path=db)
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=out,
        stderr=io.StringIO(),
        engine=eng,
        grimoire=g,
    )
    s._handle_tools_list({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tools_list = json.loads(out.getvalue().splitlines()[-1])["result"]["tools"]
    names = [t["name"] for t in tools_list]
    assert "crystallized_sigils" in names


def test_mcp_crystallized_sigils_call_succeeds(tmp_path):
    db = tmp_path / "mcp2.db"
    eng = ResonanceEngine(CompositionEngine(), backend=None)
    g = Grimoire(db_path=db)
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=out,
        stderr=io.StringIO(),
        engine=eng,
        grimoire=g,
    )
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "crystallized_sigils", "arguments": {}},
        }
    )
    resp = json.loads(out.getvalue().splitlines()[-1])
    assert resp["id"] == 2
    assert "result" in resp
    assert isinstance(resp["result"], list)

