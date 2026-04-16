from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ev = subs.add_parser("events", help="Tail recent observability events.")
    ev.add_argument("--tail", type=int, default=50, dest="tail")
    ev.add_argument("--type", default=None, dest="event_type")


def _dispatch_events(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    rows = cli._tools.tool_events_tail(n=int(ns.tail), event_type=ns.event_type)
    print(json.dumps(rows, indent=2))


DISPATCH = {"events": _dispatch_events}
