"""Decide command handlers."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from vermyth.cli.format import format_cast_result

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_decide(
    cli: "VermythCLI",
    *,
    objective: str,
    scope: str,
    reversibility: str,
    side_effect_tolerance: str,
    aspects: list[str] | None = None,
    vector: list[float] | None = None,
    parent_cast_id: str | None = None,
    causal_root_cast_id: str | None = None,
    policy_model: str | None = None,
    tuned_thresholds_path: str | None = None,
) -> None:
    try:
        out = cli._tools.tool_decide(
            intent={
                "objective": objective,
                "scope": scope,
                "reversibility": reversibility,
                "side_effect_tolerance": side_effect_tolerance,
            },
            aspects=aspects,
            vector=vector,
            parent_cast_id=parent_cast_id,
            causal_root_cast_id=causal_root_cast_id,
            policy_model=policy_model,
            tuned_thresholds_path=tuned_thresholds_path,
        )
        decision = out["decision"]
        cast = out["cast"]
        print(f"Decision: {decision['action']}")
        print(f"Rationale: {decision['rationale']}")
        print("")
        print(format_cast_result(cast))
    except KeyError as exc:
        print(f"Cast not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        if (
            type(exc).__name__ == "ValidationError"
            and type(exc).__module__.startswith("pydantic")
        ):
            print(str(exc), file=sys.stderr)
            sys.exit(1)
        raise


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    dc = subs.add_parser("decide", help="Policy decision gateway over cast evaluation.")
    dc.add_argument("--objective", required=True, metavar="TEXT")
    dc.add_argument("--scope", required=True, metavar="TEXT")
    dc.add_argument(
        "--reversibility",
        required=True,
        choices=["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
    )
    dc.add_argument(
        "--side-effect-tolerance",
        required=True,
        choices=["NONE", "LOW", "MEDIUM", "HIGH"],
        dest="side_effect_tolerance",
    )
    dc.add_argument("--aspects", nargs="+", default=None, metavar="ASPECT")
    dc.add_argument("--vector", nargs="+", type=float, default=None, metavar="F")
    dc.add_argument("--parent-cast-id", type=str, default=None, dest="parent_cast_id")
    dc.add_argument(
        "--causal-root-cast-id",
        type=str,
        default=None,
        dest="causal_root_cast_id",
    )
    dc.add_argument(
        "--policy-model",
        choices=["rule_based", "threshold_tuned"],
        default=None,
        dest="policy_model",
    )
    dc.add_argument(
        "--tuned-thresholds",
        default=None,
        dest="tuned_thresholds_path",
    )


def _dispatch_decide(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_decide(
        objective=ns.objective,
        scope=ns.scope,
        reversibility=ns.reversibility,
        side_effect_tolerance=ns.side_effect_tolerance,
        aspects=(list(ns.aspects) if ns.aspects is not None else None),
        vector=(list(ns.vector) if ns.vector is not None else None),
        parent_cast_id=ns.parent_cast_id,
        causal_root_cast_id=ns.causal_root_cast_id,
        policy_model=ns.policy_model,
        tuned_thresholds_path=ns.tuned_thresholds_path,
    )


DISPATCH = {"decide": _dispatch_decide}


