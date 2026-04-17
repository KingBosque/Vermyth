import pytest

from vermyth.cli.format import (
    format_cast_result,
    format_cast_table,
    format_search_table,
    format_seed_table,
    format_crystallized_sigils_table,
    format_divergence_report,
    format_divergence_thresholds,
    format_drift_branches_table,
    format_lineage_drift,
    format_registered_sigils_table,
    resonance_bar,
)
from vermyth.cli.main import VermythCLI
from vermyth.contracts import CLIContract



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
    assert names == {
        "decide",
        "cast",
        "fluid-cast",
        "query",
        "search",
        "inspect",
        "lineage",
        "seeds",
        "sigils",
        "register-aspect",
        "register-sigil",
        "aspects",
        "registered-sigils",
        "divergence",
        "set-thresholds",
        "thresholds",
        "divergences",
        "drift-branches",
        "lineage-drift",
        "backfill-divergence",
        "channel",
        "sync",
        "geometric-cast",
        "encode",
        "decode",
        "events",
        "auto-cast",
        "swarm-join",
        "swarm-cast",
        "swarm-status",
        "gossip-sync",
        "compile-program",
        "execute-program",
        "program-status",
        "list-programs",
        "execution-status",
        "execution-receipt",
        "receipt-verify",
        "propose-genesis",
        "genesis-proposals",
        "accept-genesis",
        "review-genesis",
        "reject-genesis",
        "infer-cause",
        "add-cause",
        "arcane-bundle-report",
        "causal-graph",
        "evaluate-narrative",
        "predictive-cast",
    }


def test_run_no_args_exits_2(capsys):
    with pytest.raises(SystemExit) as exc:
        VermythCLI().run([])
    assert exc.value.code == 2


def test_cmd_search_happy_path(make_cli, capsys):
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
    make_cli.run(
        [
            "search",
            "--vector",
            "0",
            "0",
            "0",
            "1",
            "0",
            "1",
            "--threshold",
            "0.0",
            "--limit",
            "10",
        ]
    )
    out = capsys.readouterr().out
    assert "CAST ID" in out or "No results" in out


def test_cmd_register_aspect_and_list(make_cli, capsys):
    make_cli.run(["register-aspect", "FIRE", "--polarity", "1", "--entropy", "0.5", "--symbol", "🔥"])
    make_cli.run(["aspects"])
    out = capsys.readouterr().out
    assert "FIRE" in out


def test_cmd_register_sigil_and_list(make_cli, capsys):
    make_cli.run(
        [
            "register-sigil",
            "MyOverride",
            "--aspects",
            "MIND",
            "LIGHT",
            "--effect-class",
            "REVELATION",
            "--resonance-ceiling",
            "0.9",
            "--contradiction-severity",
            "NONE",
            "--allow-override",
        ]
    )
    make_cli.run(["registered-sigils"])
    out = capsys.readouterr().out
    assert "MyOverride" in out


def test_cmd_divergence_thresholds_roundtrip(make_cli, capsys):
    make_cli.run(["thresholds"])
    before = capsys.readouterr().out
    assert "L2_STABLE_MAX" in before or "cosine" in before.lower()
    make_cli.run(["set-thresholds", "--l2-stable", "0.1", "--l2-diverged", "0.2"])
    out = capsys.readouterr().out
    assert "0.1" in out or "0.10" in out


def test_cli_entrypoint_main_callable():
    from vermyth.cli.main import main

    assert callable(main)


def test_format_crystallized_sigils_table_empty():
    assert format_crystallized_sigils_table([]) == "No crystallized sigils."


def test_format_crystallized_sigils_table_non_empty():
    out = format_crystallized_sigils_table(
        [
            {
                "name": "Glyph:Verite",
                "aspects": ["LIGHT"],
                "effect_class": "REVELATION",
                "resonance_ceiling": 0.88,
                "generation": 1,
                "crystallized_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )
    assert "Glyph:Verite" in out
    assert "CRYSTALLIZED_AT" in out


def test_format_divergence_report_shape():
    out = format_divergence_report(
        {
            "cast_id": "01ABCDEF",
            "parent_cast_id": "01PARENT",
            "l2_magnitude": 0.42,
            "cosine_distance": 0.12,
            "status": "DRIFTING",
            "computed_at": "2026-01-01T00:00:00+00:00",
        }
    )
    assert "01ABCDEF" in out
    assert "DRIFTING" in out


def test_format_divergence_thresholds_shape():
    out = format_divergence_thresholds(
        {
            "l2_stable_max": 0.1,
            "l2_diverged_min": 0.2,
            "cosine_stable_max": 0.3,
            "cosine_diverged_min": 0.4,
        }
    )
    assert "l2_stable_max" in out
    assert "0.100" in out or "0.10" in out


def test_format_drift_branches_table_empty():
    assert format_drift_branches_table([]) == "No branch drift data."


def test_format_drift_branches_table_non_empty():
    out = format_drift_branches_table(
        [
            {
                "branch_id": "branch-a",
                "worst_status": "DRIFTING",
                "worst_l2": 0.2,
                "worst_cosine": 0.1,
                "reports_count": 3,
                "latest_computed_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )
    assert "branch-a" in out


def test_format_lineage_drift_shape():
    out = format_lineage_drift(
        {
            "cast_id": "01CHILD",
            "chain_length": 2,
            "hops": [
                {"cast_id": "01PARENT", "status": "STABLE", "l2_magnitude": 0.0, "cosine_distance": 0.0},
                {"cast_id": "01CHILD", "status": "DRIFTING", "l2_magnitude": 0.2, "cosine_distance": 0.1},
            ],
            "worst_hops": [
                {"cast_id": "01CHILD", "status": "DRIFTING", "l2_magnitude": 0.2, "cosine_distance": 0.1}
            ],
        }
    )
    assert "01CHILD" in out


def test_format_registered_sigils_table_empty():
    assert format_registered_sigils_table([]) == "No registered sigils."


def test_format_registered_sigils_table_non_empty():
    out = format_registered_sigils_table(
        [
            {
                "name": "MyOverride",
                "aspects": ["MIND", "LIGHT"],
                "effect_class": "REVELATION",
                "resonance_ceiling": 0.9,
                "contradiction_severity": "NONE",
                "is_override": True,
                "registered_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )
    assert "MyOverride" in out

