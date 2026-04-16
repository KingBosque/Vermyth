from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_swarm_join(
    cli: "VermythCLI", swarm_id: str, session_id: str, *, consensus_threshold: float = 0.75
) -> None:
    try:
        out = cli._tools.tool_swarm_join(
            swarm_id=swarm_id,
            session_id=session_id,
            consensus_threshold=consensus_threshold,
        )
        print(out)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_swarm_cast(
    cli: "VermythCLI",
    swarm_id: str,
    session_id: str,
    vector: list[float],
    objective: str,
    scope: str,
    reversibility: str,
    side_effect_tolerance: str,
    *,
    consensus_threshold: Optional[float] = None,
) -> None:
    try:
        out = cli._tools.tool_swarm_cast(
            swarm_id=swarm_id,
            session_id=session_id,
            vector=vector,
            intent={
                "objective": objective,
                "scope": scope,
                "reversibility": reversibility,
                "side_effect_tolerance": side_effect_tolerance,
            },
            consensus_threshold=consensus_threshold,
        )
        print(out)
    except (ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_swarm_status(cli: "VermythCLI", swarm_id: str) -> None:
    try:
        out = cli._tools.tool_swarm_status(swarm_id=swarm_id)
        print(out)
    except KeyError:
        print(f"Swarm not found: {swarm_id}", file=sys.stderr)
        sys.exit(1)


def cmd_gossip_sync(cli: "VermythCLI", path: str) -> None:
    try:
        raw = Path(path).read_text(encoding="utf-8")
        payload = json.loads(raw)
        out = cli._tools.tool_gossip_sync(payload)
        print(out)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    sj = subs.add_parser("swarm-join", help="Create or join a swarm for consensus casting.")
    sj.add_argument("swarm_id", metavar="SWARM_ID")
    sj.add_argument("session_id", metavar="SESSION_ID")
    sj.add_argument("--consensus-threshold", type=float, default=0.75, dest="consensus_threshold")

    sc = subs.add_parser("swarm-cast", help="Cast into a swarm with weighted aggregation.")
    sc.add_argument("swarm_id", metavar="SWARM_ID")
    sc.add_argument("session_id", metavar="SESSION_ID")
    sc.add_argument("--vector", nargs="+", type=float, required=True)
    sc.add_argument("--objective", required=True)
    sc.add_argument("--scope", required=True)
    sc.add_argument(
        "--reversibility",
        required=True,
        choices=["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
    )
    sc.add_argument(
        "--side-effect-tolerance",
        required=True,
        choices=["NONE", "LOW", "MEDIUM", "HIGH"],
        dest="side_effect_tolerance",
    )
    sc.add_argument("--consensus-threshold", type=float, default=None, dest="consensus_threshold")

    ss = subs.add_parser("swarm-status", help="Show swarm aggregate and members.")
    ss.add_argument("swarm_id", metavar="SWARM_ID")

    gs = subs.add_parser("gossip-sync", help="Apply federation gossip from a JSON file.")
    gs.add_argument("path", metavar="PATH")


def _dispatch_swarm_join(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_swarm_join(
        swarm_id=ns.swarm_id,
        session_id=ns.session_id,
        consensus_threshold=float(ns.consensus_threshold),
    )


def _dispatch_swarm_cast(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_swarm_cast(
        swarm_id=ns.swarm_id,
        session_id=ns.session_id,
        vector=list(ns.vector),
        objective=ns.objective,
        scope=ns.scope,
        reversibility=ns.reversibility,
        side_effect_tolerance=ns.side_effect_tolerance,
        consensus_threshold=ns.consensus_threshold,
    )


def _dispatch_swarm_status(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_swarm_status(swarm_id=ns.swarm_id)


def _dispatch_gossip_sync(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_gossip_sync(path=ns.path)


DISPATCH = {
    "swarm-join": _dispatch_swarm_join,
    "swarm-cast": _dispatch_swarm_cast,
    "swarm-status": _dispatch_swarm_status,
    "gossip-sync": _dispatch_gossip_sync,
}
