from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Callable

from vermyth.cli.commands import bundle_report as bundle_report_commands
from vermyth.cli.commands import auto_cast as auto_cast_commands
from vermyth.cli.commands import cast as cast_commands
from vermyth.cli.commands import causal as causal_commands
from vermyth.cli.commands import decide as decide_commands
from vermyth.cli.commands import drift as drift_commands
from vermyth.cli.commands import events as events_commands
from vermyth.cli.commands import genesis as genesis_commands
from vermyth.cli.commands import programs as program_commands
from vermyth.cli.commands import query as query_commands
from vermyth.cli.commands import registry as registry_commands
from vermyth.cli.commands import session as session_commands
from vermyth.cli.commands import swarm as swarm_commands

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


COMMAND_FAMILIES = [
    bundle_report_commands,
    cast_commands,
    decide_commands,
    query_commands,
    registry_commands,
    drift_commands,
    session_commands,
    events_commands,
    auto_cast_commands,
    swarm_commands,
    program_commands,
    genesis_commands,
    causal_commands,
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vermyth",
        description="Vermyth semantic execution language for AI systems.",
    )
    subs = parser.add_subparsers(dest="command", required=True)
    for family in COMMAND_FAMILIES:
        family.register_subparsers(subs)
    return parser


def run(cli: "VermythCLI", args: list[str] | None = None) -> None:
    ns = build_parser().parse_args(args)
    dispatch: dict[str, Callable[["VermythCLI", argparse.Namespace], None]] = {}
    for family in COMMAND_FAMILIES:
        dispatch.update(family.DISPATCH)
    handler = dispatch.get(str(ns.command))
    if handler is None:
        raise SystemExit(2)
    handler(cli, ns)
