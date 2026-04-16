from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_propose_genesis(
    cli: "VermythCLI",
    *,
    history_limit: int = 500,
    min_cluster_size: int = 15,
    min_unexplained_variance: float = 0.3,
) -> None:
    try:
        out = cli._tools.tool_propose_genesis(
            history_limit=history_limit,
            min_cluster_size=min_cluster_size,
            min_unexplained_variance=min_unexplained_variance,
        )
        print(out)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_genesis_proposals(
    cli: "VermythCLI", *, status: str | None = None, limit: int = 50
) -> None:
    try:
        out = cli._tools.tool_genesis_proposals(status=status, limit=limit)
        print(out)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_accept_genesis(cli: "VermythCLI", genesis_id: str) -> None:
    try:
        out = cli._tools.tool_accept_genesis(genesis_id=genesis_id)
        print(out)
    except KeyError:
        print(f"Genesis proposal not found: {genesis_id}", file=sys.stderr)
        sys.exit(1)


def cmd_reject_genesis(cli: "VermythCLI", genesis_id: str) -> None:
    try:
        out = cli._tools.tool_reject_genesis(genesis_id=genesis_id)
        print(out)
    except KeyError:
        print(f"Genesis proposal not found: {genesis_id}", file=sys.stderr)
        sys.exit(1)


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    pg = subs.add_parser("propose-genesis", help="Propose emergent aspects from cast history.")
    pg.add_argument("--history-limit", type=int, default=500, dest="history_limit")
    pg.add_argument("--min-cluster-size", type=int, default=15, dest="min_cluster_size")
    pg.add_argument(
        "--min-unexplained-variance",
        type=float,
        default=0.3,
        dest="min_unexplained_variance",
    )

    gp = subs.add_parser("genesis-proposals", help="List emergent aspect proposals.")
    gp.add_argument("--status", default=None)
    gp.add_argument("--limit", type=int, default=50)

    ag = subs.add_parser("accept-genesis", help="Accept and register an emergent aspect.")
    ag.add_argument("genesis_id", metavar="GENESIS_ID")

    rg = subs.add_parser("reject-genesis", help="Reject an emergent aspect proposal.")
    rg.add_argument("genesis_id", metavar="GENESIS_ID")


def _dispatch_propose_genesis(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_propose_genesis(
        history_limit=int(ns.history_limit),
        min_cluster_size=int(ns.min_cluster_size),
        min_unexplained_variance=float(ns.min_unexplained_variance),
    )


def _dispatch_genesis_proposals(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_genesis_proposals(status=ns.status, limit=int(ns.limit))


def _dispatch_accept_genesis(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_accept_genesis(genesis_id=ns.genesis_id)


def _dispatch_reject_genesis(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_reject_genesis(genesis_id=ns.genesis_id)


DISPATCH = {
    "propose-genesis": _dispatch_propose_genesis,
    "genesis-proposals": _dispatch_genesis_proposals,
    "accept-genesis": _dispatch_accept_genesis,
    "reject-genesis": _dispatch_reject_genesis,
}
