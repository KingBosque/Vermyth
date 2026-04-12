import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

from vermyth.cli.format import (
    format_cast_result,
    format_cast_table,
    format_search_table,
    format_seed_table,
    resonance_bar,
)
from vermyth.cli.main import VermythCLI
from vermyth.contracts import CLIContract
from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire


@pytest.fixture
def make_cli(tmp_path):
    db = tmp_path / "cli.db"
    eng = ResonanceEngine(CompositionEngine(), None)
    g = Grimoire(db_path=db)
    return VermythCLI(engine=eng, grimoire=g)


def test_vermyth_cli_importable():
    from vermyth.cli.main import VermythCLI as C

    assert C is VermythCLI


def test_vermyth_cli_subclass_cli_contract():
    assert issubclass(VermythCLI, CLIContract)


def test_format_imports():
    from vermyth.cli import format as fmt

    assert fmt.format_cast_result is format_cast_result
    assert fmt.format_cast_table is format_cast_table
    assert fmt.format_seed_table is format_seed_table


def test_resonance_bar_width_exact():
    assert len(resonance_bar(0.5, 20)) == 20


def test_resonance_bar_zero():
    assert resonance_bar(0.0, 12) == "░" * 12


def test_resonance_bar_one():
    assert resonance_bar(1.0, 12) == "█" * 12


def test_resonance_bar_half_width_10():
    b = resonance_bar(0.5, 10)
    assert b.count("█") == 5
    assert b.count("░") == 5


def test_format_cast_table_empty():
    assert format_cast_table([]) == "No results."


def test_format_seed_table_empty():
    assert format_seed_table([]) == "No seeds found."


def test_format_search_table_with_similarities():
    rows = [
        {
            "cast_id": "01ABCDEF",
            "sigil_name": "Test",
            "verdict": "COHERENT",
            "resonance": 0.9,
        }
    ]
    out = format_search_table(rows, similarities=[0.88])
    assert "SIMILARITY" in out
    assert "0.8800" in out


def test_cmd_cast_via_run_prints_sigil_and_verdict(make_cli, capsys):
    make_cli.run(
        [
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
        ]
    )
    out = capsys.readouterr().out
    assert "Sigil" in out
    assert "Verdict" in out


def test_cmd_cast_invalid_aspect_exits_1(make_cli, capsys):
    with pytest.raises(SystemExit) as exc:
        make_cli.run(
            [
                "cast",
                "--aspects",
                "MIND",
                "XYZZY",
                "--objective",
                "x",
                "--scope",
                "y",
                "--reversibility",
                "REVERSIBLE",
                "--side-effect-tolerance",
                "HIGH",
            ]
        )
    assert exc.value.code == 1
    assert "Unknown aspect" in capsys.readouterr().err


def test_cmd_query_empty_grimoire(make_cli, capsys):
    make_cli.run(["query", "--limit", "20"])
    assert "No results." in capsys.readouterr().out


def test_cmd_query_after_cast_one_row(make_cli, capsys):
    make_cli.run(
        [
            "cast",
            "--aspects",
            "MIND",
            "LIGHT",
            "--objective",
            "study",
            "--scope",
            "local",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
        ]
    )
    capsys.readouterr()
    make_cli.run(["query", "--limit", "20"])
    out = capsys.readouterr().out
    assert "CAST ID" in out
    assert "MIND" in out or "LIGHT" in out or "Sigil" not in out


def test_cmd_inspect_unknown_exits_1(make_cli, capsys):
    with pytest.raises(SystemExit) as exc:
        make_cli.run(["inspect", "not-a-real-cast-id"])
    assert exc.value.code == 1
    assert "Cast not found" in capsys.readouterr().err


def test_cmd_inspect_after_cast(make_cli, capsys):
    make_cli.run(
        [
            "cast",
            "--aspects",
            "MIND",
            "LIGHT",
            "--objective",
            "study",
            "--scope",
            "local",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
        ]
    )
    cid = None
    for line in capsys.readouterr().out.splitlines():
        if line.strip().startswith("Cast ID"):
            cid = line.split("Cast ID", 1)[1].strip()
            break
    assert cid
    make_cli.run(["inspect", cid])
    assert cid in capsys.readouterr().out


def test_cmd_seeds_empty(make_cli, capsys):
    make_cli.run(["seeds"])
    assert "No seeds found." in capsys.readouterr().out


def test_cmd_seeds_after_cast(make_cli, capsys):
    make_cli.run(
        [
            "cast",
            "--aspects",
            "MIND",
            "LIGHT",
            "--objective",
            "study",
            "--scope",
            "local",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
        ]
    )
    capsys.readouterr()
    make_cli.run(["seeds"])
    out = capsys.readouterr().out
    assert "SEED ID" in out
    assert "accumulating" in out or "crystallized" in out


def test_build_parser_subcommands(make_cli):
    p = make_cli.build_parser()
    names = set()
    for action in p._actions:
        ch = getattr(action, "choices", None)
        if ch:
            names = set(ch.keys())
            break
    assert names == {"cast", "query", "search", "inspect", "seeds"}


def test_run_no_args_exits_2(capsys):
    with pytest.raises(SystemExit) as exc:
        VermythCLI().run([])
    assert exc.value.code == 2
