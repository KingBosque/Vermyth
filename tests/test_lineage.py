"""Lineage chain: tool_cast parent linkage, branch inheritance, tool_lineage, CLI, MCP."""

import io
import json
from pathlib import Path

import pytest

from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.cli.format import format_lineage_chain
from vermyth.cli.main import VermythCLI
from vermyth.mcp.protocol import ERROR_INVALID_PARAMS
from vermyth.mcp.server import VermythMCPServer
from vermyth.mcp.tools import VermythTools


def _intent():
    return {
        "objective": "study the pattern",
        "scope": "local workspace",
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "HIGH",
    }


def test_cast_without_parent_has_no_lineage(make_tools):
    out = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_intent())
    assert out["lineage"] is None


def test_cast_with_parent_lineage_depth_and_divergence(make_tools):
    parent = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_intent())
    pid = parent["cast_id"]
    child = make_tools.tool_cast(
        aspects=["MIND", "LIGHT"],
        intent=_intent(),
        parent_cast_id=pid,
    )
    lin = child["lineage"]
    assert lin is not None
    assert lin["depth"] == 1
    assert lin["parent_cast_id"] == pid
    assert lin["branch_id"]
    assert lin["divergence_vector"] is not None
    assert len(lin["divergence_vector"]) == 6
    assert lin.get("divergence") is not None
    assert lin["divergence"]["status"] in {"STABLE", "DRIFTING", "DIVERGED"}


def test_chain_three_casts_increments_depth(make_tools):
    r1 = make_tools.tool_cast(aspects=["VOID", "FORM"], intent=_intent())
    r2 = make_tools.tool_cast(
        aspects=["VOID", "FORM"],
        intent=_intent(),
        parent_cast_id=r1["cast_id"],
    )
    r3 = make_tools.tool_cast(
        aspects=["VOID", "FORM"],
        intent=_intent(),
        parent_cast_id=r2["cast_id"],
    )
    assert r2["lineage"]["depth"] == 1
    assert r3["lineage"]["depth"] == 2
    assert r3["lineage"]["parent_cast_id"] == r2["cast_id"]


def test_branch_inherited_when_parent_has_lineage(make_tools):
    r1 = make_tools.tool_cast(aspects=["MIND", "DECAY"], intent=_intent())
    r2 = make_tools.tool_cast(
        aspects=["MIND", "DECAY"],
        intent=_intent(),
        parent_cast_id=r1["cast_id"],
    )
    b = r2["lineage"]["branch_id"]
    r3 = make_tools.tool_cast(
        aspects=["MIND", "DECAY"],
        intent=_intent(),
        parent_cast_id=r2["cast_id"],
    )
    assert r3["lineage"]["branch_id"] == b


def test_explicit_branch_id_on_child(make_tools):
    r1 = make_tools.tool_cast(aspects=["LIGHT", "VOID"], intent=_intent())
    r2 = make_tools.tool_cast(
        aspects=["LIGHT", "VOID"],
        intent=_intent(),
        parent_cast_id=r1["cast_id"],
        branch_id="EXPLICIT_BRANCH_X",
    )
    assert r2["lineage"]["branch_id"] == "EXPLICIT_BRANCH_X"


def test_tool_lineage_root_first_order(tmp_path):
    db = tmp_path / "chain.db"
    composition = CompositionEngine()
    engine = ResonanceEngine(composition, backend=None)
    grimoire = Grimoire(db_path=db)
    tools = VermythTools(engine, grimoire)
    r1 = tools.tool_cast(aspects=["MOTION", "LIGHT"], intent=_intent())
    r2 = tools.tool_cast(
        aspects=["MOTION", "LIGHT"],
        intent=_intent(),
        parent_cast_id=r1["cast_id"],
    )
    r3 = tools.tool_cast(
        aspects=["MOTION", "LIGHT"],
        intent=_intent(),
        parent_cast_id=r2["cast_id"],
    )
    chain = tools.tool_lineage(r3["cast_id"])
    assert [c["cast_id"] for c in chain] == [r1["cast_id"], r2["cast_id"], r3["cast_id"]]


def test_tool_lineage_unknown_cast_raises(make_tools):
    with pytest.raises(KeyError):
        make_tools.tool_lineage("no-such-cast-id-xyz")


def test_tool_lineage_respects_max_depth(make_tools):
    r1 = make_tools.tool_cast(aspects=["FORM", "LIGHT"], intent=_intent())
    r2 = make_tools.tool_cast(
        aspects=["FORM", "LIGHT"],
        intent=_intent(),
        parent_cast_id=r1["cast_id"],
    )
    chain = make_tools.tool_lineage(r2["cast_id"], max_depth=1)
    assert len(chain) == 1
    assert chain[0]["cast_id"] == r2["cast_id"]


def test_cmd_cast_parent_shows_lineage_block(make_cli, capsys):
    make_cli.run(
        [
            "cast",
            "--aspects",
            "MIND",
            "LIGHT",
            "--objective",
            "a",
            "--scope",
            "b",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
        ]
    )
    out1 = capsys.readouterr().out
    parent_id = out1.split("Cast ID", 1)[1].strip().split()[0]
    make_cli.run(
        [
            "cast",
            "--aspects",
            "MIND",
            "LIGHT",
            "--objective",
            "a",
            "--scope",
            "b",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
            "--parent",
            parent_id,
        ]
    )
    out2 = capsys.readouterr().out
    assert "Lineage" in out2
    assert "parent:" in out2
    assert parent_id in out2


def test_cmd_cast_invalid_parent_exits_1(make_cli, capsys):
    with pytest.raises(SystemExit) as exc:
        make_cli.run(
            [
                "cast",
                "--aspects",
                "MIND",
                "LIGHT",
                "--objective",
                "a",
                "--scope",
                "b",
                "--reversibility",
                "REVERSIBLE",
                "--side-effect-tolerance",
                "HIGH",
                "--parent",
                "not-a-real-parent-id",
            ]
        )
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Cast not found" in err
    assert "not-a-real-parent-id" in err


def test_cmd_lineage_prints_format_lineage_chain(make_cli, capsys):
    make_cli.run(
        [
            "cast",
            "--aspects",
            "MIND",
            "LIGHT",
            "--objective",
            "a",
            "--scope",
            "b",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
        ]
    )
    out1 = capsys.readouterr().out
    cid = out1.split("Cast ID", 1)[1].strip().split()[0]
    make_cli.run(["lineage", cid])
    out = capsys.readouterr().out
    assert "[0]" in out
    assert cid[:14] in out


def test_format_lineage_chain_non_empty(make_tools):
    r1 = make_tools.tool_cast(aspects=["VOID", "LIGHT"], intent=_intent())
    r2 = make_tools.tool_cast(
        aspects=["VOID", "LIGHT"],
        intent=_intent(),
        parent_cast_id=r1["cast_id"],
    )
    chain = make_tools.tool_lineage(r2["cast_id"])
    text = format_lineage_chain(chain)
    assert "divergence from parent" in text
    assert r1["cast_id"][:14] in text


def _mcp(tmp_path):
    db = tmp_path / "mcp.db"
    eng = ResonanceEngine(CompositionEngine(), None)
    g = Grimoire(db_path=db)
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=out,
        stderr=io.StringIO(),
        engine=eng,
        grimoire=g,
    )
    return s, out


def _last_json_line(stdout: io.StringIO) -> dict:
    """Parse the last JSON object from newline-delimited MCP stdout."""
    stdout.seek(0)
    lines = [ln for ln in stdout.getvalue().splitlines() if ln.strip()]
    return json.loads(lines[-1])


def test_mcp_cast_with_parent_returns_lineage(tmp_path):
    s, out = _mcp(tmp_path)
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "cast",
                "arguments": {
                    "aspects": ["MIND", "LIGHT"],
                    **_intent(),
                },
            },
        }
    )
    parent = _last_json_line(out)["result"]
    pid = parent["cast_id"]
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "cast",
                "arguments": {
                    "aspects": ["MIND", "LIGHT"],
                    **_intent(),
                    "parent_cast_id": pid,
                },
            },
        }
    )
    child = _last_json_line(out)["result"]
    assert child["lineage"] is not None
    assert child["lineage"]["parent_cast_id"] == pid
    assert child["lineage"]["divergence_vector"]
    assert child["lineage"].get("divergence") is not None


def test_mcp_cast_invalid_parent_invalid_params(tmp_path):
    s, out = _mcp(tmp_path)
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "cast",
                "arguments": {
                    "aspects": ["MIND", "LIGHT"],
                    **_intent(),
                    "parent_cast_id": "missing-parent-cast",
                },
            },
        }
    )
    resp = _last_json_line(out)
    assert "error" in resp
    assert resp["error"]["code"] == ERROR_INVALID_PARAMS
    assert "missing-parent-cast" in resp["error"]["message"] or "Not found" in resp[
        "error"
    ]["message"]


def test_mcp_lineage_tool_returns_chain(tmp_path):
    s, out = _mcp(tmp_path)
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "cast",
                "arguments": {"aspects": ["VOID", "FORM"], **_intent()},
            },
        }
    )
    r1 = _last_json_line(out)["result"]
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "cast",
                "arguments": {
                    "aspects": ["VOID", "FORM"],
                    **_intent(),
                    "parent_cast_id": r1["cast_id"],
                },
            },
        }
    )
    r2 = _last_json_line(out)["result"]
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "lineage",
                "arguments": {"cast_id": r2["cast_id"]},
            },
        }
    )
    chain = _last_json_line(out)["result"]
    assert isinstance(chain, list)
    assert len(chain) == 2
    assert chain[0]["cast_id"] == r1["cast_id"]
    assert chain[1]["cast_id"] == r2["cast_id"]
