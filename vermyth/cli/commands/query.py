from __future__ import annotations

import argparse
import sys
from typing import Optional, TYPE_CHECKING

from vermyth.cli.format import (
    format_cast_result,
    format_cast_table,
    format_crystallized_sigils_table,
    format_lineage_chain,
    format_search_table,
    format_seed_table,
)
from vermyth.schema import SemanticVector

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_query(
    cli: "VermythCLI",
    *,
    verdict_filter: Optional[str] = None,
    min_resonance: Optional[float] = None,
    branch_id: Optional[str] = None,
    limit: int = 20,
) -> None:
    try:
        filters = {
            "verdict_filter": verdict_filter,
            "min_resonance": min_resonance,
            "branch_id": branch_id,
            "limit": limit,
        }
        rows = cli._tools.tool_query(filters)
        print(format_cast_table(rows))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_search(cli: "VermythCLI", vector: list[float], threshold: float, limit: int) -> None:
    try:
        rows = cli._tools.tool_semantic_search(
            proximity_vector=vector,
            threshold=threshold,
            limit=limit,
        )
        print(format_search_table(rows))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_inspect(cli: "VermythCLI", cast_id: str) -> None:
    try:
        row = cli._tools.tool_inspect(cast_id=cast_id)
        print(format_cast_result(row))
    except KeyError:
        print(f"Cast not found: {cast_id}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_lineage(cli: "VermythCLI", cast_id: str, max_depth: int) -> None:
    try:
        rows = cli._tools.tool_lineage(cast_id=cast_id, max_depth=max_depth)
        print(format_lineage_chain(rows))
    except KeyError:
        print(f"Cast not found: {cast_id}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_seeds(cli: "VermythCLI", crystallized: Optional[bool]) -> None:
    try:
        rows = cli._tools.tool_seeds(crystallized=crystallized)
        print(format_seed_table(rows))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_crystallized_sigils(cli: "VermythCLI") -> None:
    try:
        rows = cli._tools.tool_crystallized_sigils()
        print(format_crystallized_sigils_table(rows))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    q = subs.add_parser("query", help="Query stored casts.")
    q.add_argument(
        "--verdict",
        choices=["COHERENT", "PARTIAL", "INCOHERENT"],
        default=None,
    )
    q.add_argument("--min-resonance", type=float, default=None, dest="min_resonance")
    q.add_argument("--branch-id", default=None, dest="branch_id")
    q.add_argument("--limit", type=int, default=20)

    s = subs.add_parser("search", help="Semantic search over casts.")
    s.add_argument("--vector", nargs=6, type=float, required=True, metavar="F")
    s.add_argument("--threshold", type=float, required=True)
    s.add_argument("--limit", type=int, default=20)

    i = subs.add_parser("inspect", help="Inspect one cast by id.")
    i.add_argument("cast_id", metavar="CAST_ID")

    lin = subs.add_parser("lineage", help="Print lineage chain from a cast toward the root.")
    lin.add_argument("cast_id", metavar="CAST_ID")
    lin.add_argument("--max-depth", type=int, default=50, dest="max_depth")

    sd = subs.add_parser("seeds", help="List glyph seeds.")
    sd.add_argument("--crystallized", action="store_true", default=None)
    sd.add_argument("--accumulating", action="store_true", default=None)

    subs.add_parser("sigils", help="List crystallized sigils.")


def _dispatch_query(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_query(
        verdict=ns.verdict,
        min_resonance=ns.min_resonance,
        branch_id=ns.branch_id,
        limit=ns.limit,
    )


def _dispatch_search(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_search(vector=list(ns.vector), threshold=ns.threshold, limit=ns.limit)


def _dispatch_inspect(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_inspect(cast_id=ns.cast_id)


def _dispatch_lineage(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_lineage(cast_id=ns.cast_id, max_depth=ns.max_depth)


def _dispatch_seeds(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    if ns.crystallized:
        cli.cmd_seeds(crystallized=True)
    elif ns.accumulating:
        cli.cmd_seeds(crystallized=False)
    else:
        cli.cmd_seeds(crystallized=None)


def _dispatch_sigils(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    _ = ns
    cli.cmd_crystallized_sigils()


DISPATCH = {
    "query": _dispatch_query,
    "search": _dispatch_search,
    "inspect": _dispatch_inspect,
    "lineage": _dispatch_lineage,
    "seeds": _dispatch_seeds,
    "sigils": _dispatch_sigils,
}

