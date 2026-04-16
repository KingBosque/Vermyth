from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING, Optional

from vermyth.cli.format import (
    format_divergence_report,
    format_divergence_reports_table,
    format_divergence_thresholds,
    format_drift_branches_table,
    format_lineage_drift,
)
from vermyth.schema import DivergenceReport

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_divergence(cli: "VermythCLI", cast_id: str) -> None:
    try:
        report = cli._tools.tool_divergence(cast_id=cast_id)
        print(format_divergence_report(report))
    except KeyError:
        print(f"Divergence report not found: {cast_id}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_set_thresholds(
    cli: "VermythCLI",
    *,
    l2_stable_max: Optional[float],
    l2_diverged_min: Optional[float],
    cosine_stable_max: Optional[float],
    cosine_diverged_min: Optional[float],
) -> None:
    try:
        payload = {}
        if l2_stable_max is not None:
            payload["l2_stable_max"] = float(l2_stable_max)
        if l2_diverged_min is not None:
            payload["l2_diverged_min"] = float(l2_diverged_min)
        if cosine_stable_max is not None:
            payload["cosine_stable_max"] = float(cosine_stable_max)
        if cosine_diverged_min is not None:
            payload["cosine_diverged_min"] = float(cosine_diverged_min)
        updated = cli._tools.tool_set_divergence_thresholds(payload)
        print(format_divergence_thresholds(updated))
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_thresholds(cli: "VermythCLI") -> None:
    values = cli._tools.tool_divergence_thresholds()
    print(format_divergence_thresholds(values))


def cmd_divergences(
    cli: "VermythCLI",
    *,
    status: Optional[str] = None,
    limit: int = 50,
    since: Optional[str] = None,
) -> None:
    try:
        rows = cli._tools.tool_divergence_reports(
            status=status,
            limit=limit,
            since=since,
        )
        print(format_divergence_reports_table(rows))
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_drift_branches(cli: "VermythCLI", limit: int) -> None:
    rows = cli._tools.tool_drift_branches(limit=limit)
    print(format_drift_branches_table(rows))


def cmd_lineage_drift(
    cli: "VermythCLI", cast_id: str, max_depth: int, top_k: int
) -> None:
    out = cli._tools.tool_lineage_drift(
        cast_id=cast_id,
        max_depth=max_depth,
        top_k=top_k,
    )
    print(format_lineage_drift(out))


def cmd_backfill_divergence(cli: "VermythCLI", limit: int) -> None:
    pairs = cli._grimoire.cast_pairs_missing_divergence_reports(limit=int(limit))
    if not pairs:
        print("No missing divergence reports.")
        return
    processed = 0
    for cast_id, parent_cast_id in pairs:
        try:
            child = cli._grimoire.read(cast_id)
            parent = cli._grimoire.read(parent_cast_id)
            dr = cli._grimoire.read_divergence_thresholds()

            row = DivergenceReport.classify(
                cast_id=child.cast_id,
                parent_cast_id=parent.cast_id,
                parent_vector=parent.sigil.semantic_vector,
                child_vector=child.sigil.semantic_vector,
                thresholds=dr,
            )
            cli._grimoire.write_divergence_report(row)
            cli._tools._divergence_cache[child.cast_id] = row
            processed += 1
        except Exception:
            continue
    print(f"Backfilled {processed} divergence reports.")


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    d = subs.add_parser("divergence", help="Read divergence report for a cast.")
    d.add_argument("cast_id", metavar="CAST_ID")

    st = subs.add_parser("set-thresholds", help="Update divergence thresholds.")
    st.add_argument("--l2-stable", type=float, default=None, dest="l2_stable")
    st.add_argument("--l2-diverged", type=float, default=None, dest="l2_diverged")
    st.add_argument("--cosine-stable", type=float, default=None, dest="cosine_stable")
    st.add_argument("--cosine-diverged", type=float, default=None, dest="cosine_diverged")

    subs.add_parser("thresholds", help="Print active divergence thresholds.")

    dv = subs.add_parser("divergences", help="List divergence reports.")
    dv.add_argument("--status", default=None, choices=["STABLE", "DRIFTING", "DIVERGED"])
    dv.add_argument("--limit", type=int, default=50)
    dv.add_argument("--since", default=None)

    db = subs.add_parser("drift-branches", help="Rank branches by drift severity.")
    db.add_argument("--limit", type=int, default=20)

    ld = subs.add_parser("lineage-drift", help="Summarize drift across a lineage chain.")
    ld.add_argument("cast_id", metavar="CAST_ID")
    ld.add_argument("--max-depth", type=int, default=100, dest="max_depth")
    ld.add_argument("--top-k", type=int, default=5, dest="top_k")

    bf = subs.add_parser("backfill-divergence", help="Backfill missing divergence reports.")
    bf.add_argument("--limit", type=int, default=1000)


def _dispatch_divergence(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_divergence(cast_id=ns.cast_id)


def _dispatch_set_thresholds(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_set_thresholds(
        l2_stable=ns.l2_stable,
        l2_diverged=ns.l2_diverged,
        cosine_stable=ns.cosine_stable,
        cosine_diverged=ns.cosine_diverged,
    )


def _dispatch_thresholds(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    _ = ns
    cli.cmd_thresholds()


def _dispatch_divergences(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_divergences(status=ns.status, limit=ns.limit, since=ns.since)


def _dispatch_drift_branches(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_drift_branches(limit=ns.limit)


def _dispatch_lineage_drift(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_lineage_drift(cast_id=ns.cast_id, max_depth=ns.max_depth, top_k=ns.top_k)


def _dispatch_backfill_divergence(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_backfill_divergence(limit=ns.limit)


DISPATCH = {
    "divergence": _dispatch_divergence,
    "set-thresholds": _dispatch_set_thresholds,
    "thresholds": _dispatch_thresholds,
    "divergences": _dispatch_divergences,
    "drift-branches": _dispatch_drift_branches,
    "lineage-drift": _dispatch_lineage_drift,
    "backfill-divergence": _dispatch_backfill_divergence,
}

