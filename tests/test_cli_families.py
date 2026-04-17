from __future__ import annotations

from vermyth.cli import parser as cli_parser


def test_cli_families_register_all_commands() -> None:
    parser = cli_parser.build_parser()
    subparsers_action = next(
        action for action in parser._actions if action.dest == "command"
    )
    commands = set(subparsers_action.choices.keys())
    assert commands == {
        "cast",
        "decide",
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


def test_cli_dispatch_has_handler_for_every_command() -> None:
    dispatch = {}
    for family in cli_parser.COMMAND_FAMILIES:
        dispatch.update(family.DISPATCH)
    parser = cli_parser.build_parser()
    subparsers_action = next(
        action for action in parser._actions if action.dest == "command"
    )
    for command in subparsers_action.choices.keys():
        assert command in dispatch
