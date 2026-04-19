"""Opt-in arcane transcript on MCP tools and CLI (default wire/output unchanged)."""

from __future__ import annotations

import json

import pytest

from vermyth.arcane.presentation.transcript import arcane_transcript_for_cast_result


def test_tool_cast_arcane_transcript_absent_by_default(make_tools, valid_intent):
    out = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=valid_intent)
    assert "arcane_transcript" not in out


def test_tool_cast_include_arcane_transcript_matches_helper(make_tools, valid_intent):
    out = make_tools.tool_cast(
        aspects=["MIND", "LIGHT"],
        intent=valid_intent,
        include_arcane_transcript=True,
    )
    assert "arcane_transcript" in out
    tr = out["arcane_transcript"]
    assert tr["kind"] == "arcane_transcript"
    assert tr["presentation_only"] is True
    cr = make_tools._grimoire.read(out["cast_id"])
    assert tr == arcane_transcript_for_cast_result(cr)


def test_tool_fluid_cast_include_arcane_transcript_matches_helper(make_tools, valid_intent):
    out = make_tools.tool_fluid_cast(
        vector=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        intent=valid_intent,
        include_arcane_transcript=True,
    )
    cr = make_tools._grimoire.read(out["cast_id"])
    assert out["arcane_transcript"] == arcane_transcript_for_cast_result(cr)


def test_tool_auto_cast_include_arcane_transcript_matches_final_cast(make_tools, valid_intent):
    out = make_tools.tool_auto_cast(
        vector=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        intent=valid_intent,
        max_depth=3,
        include_arcane_transcript=True,
    )
    final_id = out["cast_id"]
    cr = make_tools._grimoire.read(final_id)
    assert out["arcane_transcript"] == arcane_transcript_for_cast_result(cr)


def test_dispatch_cast_passes_include_arcane_transcript(make_tools, valid_intent):
    from vermyth.mcp.tools.casting._legacy import dispatch_cast

    out = dispatch_cast(
        make_tools,
        {
            "aspects": ["MIND", "LIGHT"],
            "objective": valid_intent["objective"],
            "scope": valid_intent["scope"],
            "reversibility": valid_intent["reversibility"],
            "side_effect_tolerance": valid_intent["side_effect_tolerance"],
            "include_arcane_transcript": True,
        },
    )
    assert "arcane_transcript" in out


@pytest.mark.parametrize("flag", [[], ["--arcane-transcript"]])
def test_cmd_cast_arcane_transcript_cli(make_cli, capsys, flag: list[str]):
    argv = [
        "cast",
        "--aspects",
        "MIND",
        "LIGHT",
        "--objective",
        "study the pattern",
        "--scope",
        "local",
        "--reversibility",
        "REVERSIBLE",
        "--side-effect-tolerance",
        "HIGH",
        *flag,
    ]
    make_cli.run(argv)
    out = capsys.readouterr().out
    if flag:
        assert "Arcane transcript (presentation-only" in out
        idx = out.index("{")
        payload = json.loads(out[idx:])
        assert payload["kind"] == "arcane_transcript"
        assert payload["presentation_only"] is True
        assert [p["phase"] for p in payload["phases"]][:2] == ["attunement", "warding"]
    else:
        assert "Arcane transcript" not in out


def test_cmd_fluid_cast_arcane_transcript_flag(make_cli, capsys):
    make_cli.run(
        [
            "fluid-cast",
            "--vector",
            "0",
            "0",
            "0",
            "1",
            "0",
            "0",
            "--objective",
            "study",
            "--scope",
            "repo",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
            "--arcane-transcript",
        ]
    )
    out = capsys.readouterr().out
    assert "Arcane transcript (presentation-only" in out
    assert '"kind": "arcane_transcript"' in out
