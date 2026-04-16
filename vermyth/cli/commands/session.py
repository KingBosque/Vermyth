from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ch = subs.add_parser("channel", help="Read channel state for a branch id.")
    ch.add_argument("branch_id", metavar="BRANCH_ID")

    sy = subs.add_parser("sync", help="Sync (recover) a channel by branch id.")
    sy.add_argument("branch_id", metavar="BRANCH_ID")

    gc = subs.add_parser("geometric-cast", help="Cast using a geometric payload vector.")
    gc.add_argument("--payload", nargs="+", type=float, required=True)
    gc.add_argument("--version", type=int, default=1)
    gc.add_argument("--branch-id", default=None, dest="branch_id")
    gc.add_argument("--force", action="store_true", default=False)

    enc = subs.add_parser("encode", help="Encode intent+vector into a geometric packet.")
    enc.add_argument("--vector", nargs="+", type=float, required=True)
    enc.add_argument("--objective", required=True)
    enc.add_argument("--scope", required=True)
    enc.add_argument(
        "--reversibility",
        required=True,
        choices=["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
    )
    enc.add_argument(
        "--side-effect-tolerance",
        required=True,
        choices=["NONE", "LOW", "MEDIUM", "HIGH"],
        dest="side_effect_tolerance",
    )

    dec = subs.add_parser("decode", help="Decode a geometric packet.")
    dec.add_argument("--payload", nargs="+", type=float, required=True)
    dec.add_argument("--version", type=int, default=1)


def _dispatch_channel(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    try:
        state = cli._tools.tool_channel_status(branch_id=ns.branch_id)
        print(state)
    except KeyError:
        print(f"Channel not found: {ns.branch_id}", file=sys.stderr)
        raise SystemExit(1)


def _dispatch_sync(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    try:
        state = cli._tools.tool_sync_channel(branch_id=ns.branch_id)
        print(state)
    except KeyError:
        print(f"Channel not found: {ns.branch_id}", file=sys.stderr)
        raise SystemExit(1)


def _dispatch_geometric_cast(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_geometric_cast(
        payload=list(ns.payload),
        version=int(ns.version),
        branch_id=ns.branch_id,
        force=bool(ns.force),
    )


def _dispatch_encode(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_encode(
        vector=list(ns.vector),
        objective=ns.objective,
        scope=ns.scope,
        reversibility=ns.reversibility,
        side_effect_tolerance=ns.side_effect_tolerance,
    )


def _dispatch_decode(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_decode(payload=list(ns.payload), version=int(ns.version))


DISPATCH = {
    "channel": _dispatch_channel,
    "sync": _dispatch_sync,
    "geometric-cast": _dispatch_geometric_cast,
    "encode": _dispatch_encode,
    "decode": _dispatch_decode,
}
