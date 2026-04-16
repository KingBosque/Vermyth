from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from vermyth.cli.format import format_cast_result

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_infer_cause(cli: "VermythCLI", source_cast_id: str, target_cast_id: str) -> None:
    try:
        out = cli._tools.tool_infer_causal_edge(
            source_cast_id=source_cast_id,
            target_cast_id=target_cast_id,
        )
        print(out)
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_add_cause(cli: "VermythCLI", payload: dict[str, object]) -> None:
    try:
        out = cli._tools.tool_add_causal_edge(payload)
        print(out)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_causal_graph(
    cli: "VermythCLI",
    *,
    root_cast_id: str,
    edge_types: list[str] | None = None,
    direction: str = "both",
    max_depth: int = 5,
    min_weight: float = 0.0,
) -> None:
    out = cli._tools.tool_causal_subgraph(
        root_cast_id=root_cast_id,
        edge_types=edge_types,
        direction=direction,
        max_depth=max_depth,
        min_weight=min_weight,
    )
    print(out)


def cmd_evaluate_narrative(cli: "VermythCLI", edge_ids: list[str]) -> None:
    out = cli._tools.tool_evaluate_narrative(edge_ids=edge_ids)
    print(out)


def cmd_predictive_cast(
    cli: "VermythCLI",
    *,
    root_cast_id: str,
    objective: str,
    scope: str,
    reversibility: str,
    side_effect_tolerance: str,
) -> None:
    out = cli._tools.tool_predictive_cast(
        root_cast_id=root_cast_id,
        intent={
            "objective": objective,
            "scope": scope,
            "reversibility": reversibility,
            "side_effect_tolerance": side_effect_tolerance,
        },
    )
    print(format_cast_result(out))


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ic = subs.add_parser("infer-cause", help="Infer a causal edge between two casts.")
    ic.add_argument("source_cast_id", metavar="SOURCE_CAST_ID")
    ic.add_argument("target_cast_id", metavar="TARGET_CAST_ID")

    ad = subs.add_parser("add-cause", help="Add a causal edge manually.")
    ad.add_argument("source_cast_id", metavar="SOURCE_CAST_ID")
    ad.add_argument("target_cast_id", metavar="TARGET_CAST_ID")
    ad.add_argument(
        "--edge-type",
        required=True,
        choices=["CAUSES", "INHIBITS", "ENABLES", "REQUIRES"],
        dest="edge_type",
    )
    ad.add_argument("--weight", type=float, required=True)
    ad.add_argument("--evidence", default="")

    cg = subs.add_parser("causal-graph", help="Traverse causal graph from a root cast.")
    cg.add_argument("root_cast_id", metavar="ROOT_CAST_ID")
    cg.add_argument("--edge-types", nargs="+", default=None, dest="edge_types")
    cg.add_argument("--direction", default="both", choices=["forward", "backward", "both"])
    cg.add_argument("--max-depth", type=int, default=5, dest="max_depth")
    cg.add_argument("--min-weight", type=float, default=0.0, dest="min_weight")

    en = subs.add_parser("evaluate-narrative", help="Evaluate coherence for causal edges.")
    en.add_argument("edge_ids", nargs="+", metavar="EDGE_ID")

    pc = subs.add_parser("predictive-cast", help="Generate predictive cast from a causal root.")
    pc.add_argument("root_cast_id", metavar="ROOT_CAST_ID")
    pc.add_argument("--objective", required=True)
    pc.add_argument("--scope", required=True)
    pc.add_argument(
        "--reversibility",
        required=True,
        choices=["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
    )
    pc.add_argument(
        "--side-effect-tolerance",
        required=True,
        choices=["NONE", "LOW", "MEDIUM", "HIGH"],
        dest="side_effect_tolerance",
    )


def _dispatch_infer_cause(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_infer_cause(source_cast_id=ns.source_cast_id, target_cast_id=ns.target_cast_id)


def _dispatch_add_cause(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_add_cause(
        {
            "source_cast_id": ns.source_cast_id,
            "target_cast_id": ns.target_cast_id,
            "edge_type": ns.edge_type,
            "weight": float(ns.weight),
            "evidence": ns.evidence,
        }
    )


def _dispatch_causal_graph(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_causal_graph(
        root_cast_id=ns.root_cast_id,
        edge_types=ns.edge_types,
        direction=ns.direction,
        max_depth=int(ns.max_depth),
        min_weight=float(ns.min_weight),
    )


def _dispatch_evaluate_narrative(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_evaluate_narrative(edge_ids=list(ns.edge_ids))


def _dispatch_predictive_cast(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_predictive_cast(
        root_cast_id=ns.root_cast_id,
        objective=ns.objective,
        scope=ns.scope,
        reversibility=ns.reversibility,
        side_effect_tolerance=ns.side_effect_tolerance,
    )


DISPATCH = {
    "infer-cause": _dispatch_infer_cause,
    "add-cause": _dispatch_add_cause,
    "causal-graph": _dispatch_causal_graph,
    "evaluate-narrative": _dispatch_evaluate_narrative,
    "predictive-cast": _dispatch_predictive_cast,
}
