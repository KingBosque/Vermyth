from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from vermyth.cli.format import format_cast_result

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_cast(
    cli: "VermythCLI",
    aspects: list[str],
    objective: str,
    scope: str,
    reversibility: str,
    side_effect_tolerance: str,
    *,
    parent_cast_id: str | None = None,
    branch_id: str | None = None,
    fail_on_diverged: bool = False,
    chained: bool = False,
    force: bool = False,
) -> None:
    try:
        result = cli._tools.tool_cast(
            aspects=aspects,
            intent={
                "objective": objective,
                "scope": scope,
                "reversibility": reversibility,
                "side_effect_tolerance": side_effect_tolerance,
            },
            parent_cast_id=parent_cast_id,
            branch_id=branch_id,
            chained=bool(chained),
            force=bool(force),
        )
        print(format_cast_result(result))
        if fail_on_diverged:
            lin = result.get("lineage") or {}
            div = lin.get("divergence") or {}
            if str(div.get("status", "") or "") == "DIVERGED":
                raise SystemExit(2)
    except KeyError:
        pid = parent_cast_id or "parent"
        print(f"Cast not found: {pid}", file=sys.stderr)
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
    c = subs.add_parser("cast", help="Cast aspects with an intent.")
    c.add_argument(
        "--aspects",
        nargs="+",
        required=True,
        metavar="ASPECT",
        help="One to three aspect names. Valid: VOID FORM MOTION MIND DECAY LIGHT.",
    )
    c.add_argument("--objective", required=True, metavar="TEXT")
    c.add_argument("--scope", required=True, metavar="TEXT")
    c.add_argument(
        "--reversibility",
        required=True,
        choices=["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
    )
    c.add_argument(
        "--side-effect-tolerance",
        required=True,
        choices=["NONE", "LOW", "MEDIUM", "HIGH"],
        dest="side_effect_tolerance",
    )
    c.add_argument("--parent", type=str, default=None, dest="parent_cast_id")
    c.add_argument("--branch-id", type=str, default=None, dest="cast_branch_id")
    c.add_argument("--fail-on-diverged", action="store_true", default=False)
    c.add_argument("--chained", action="store_true", default=False)
    c.add_argument("--force", action="store_true", default=False)

    fc = subs.add_parser("fluid-cast", help="Cast from a raw semantic vector.")
    fc.add_argument("--vector", nargs="+", type=float, required=True, metavar="F")
    fc.add_argument("--objective", required=True, metavar="TEXT")
    fc.add_argument("--scope", required=True, metavar="TEXT")
    fc.add_argument(
        "--reversibility",
        required=True,
        choices=["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
    )
    fc.add_argument(
        "--side-effect-tolerance",
        required=True,
        choices=["NONE", "LOW", "MEDIUM", "HIGH"],
        dest="side_effect_tolerance",
    )
    fc.add_argument("--parent", type=str, default=None, dest="parent_cast_id")
    fc.add_argument("--branch-id", type=str, default=None, dest="cast_branch_id")
    fc.add_argument("--fail-on-diverged", action="store_true", default=False)


def _dispatch_cast(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_cast(
        aspects=ns.aspects,
        objective=ns.objective,
        scope=ns.scope,
        reversibility=ns.reversibility,
        side_effect_tolerance=ns.side_effect_tolerance,
        parent_cast_id=ns.parent_cast_id,
        branch_id=ns.cast_branch_id,
        fail_on_diverged=bool(ns.fail_on_diverged),
        chained=bool(ns.chained),
        force=bool(ns.force),
    )


def _dispatch_fluid_cast(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_fluid_cast(
        vector=list(ns.vector),
        objective=ns.objective,
        scope=ns.scope,
        reversibility=ns.reversibility,
        side_effect_tolerance=ns.side_effect_tolerance,
        parent_cast_id=ns.parent_cast_id,
        branch_id=ns.cast_branch_id,
        fail_on_diverged=bool(ns.fail_on_diverged),
    )


DISPATCH = {
    "cast": _dispatch_cast,
    "fluid-cast": _dispatch_fluid_cast,
}


def cmd_fluid_cast(
    cli: "VermythCLI",
    vector: list[float],
    objective: str,
    scope: str,
    reversibility: str,
    side_effect_tolerance: str,
    *,
    parent_cast_id: str | None = None,
    branch_id: str | None = None,
    fail_on_diverged: bool = False,
) -> None:
    try:
        result = cli._tools.tool_fluid_cast(
            vector=vector,
            intent={
                "objective": objective,
                "scope": scope,
                "reversibility": reversibility,
                "side_effect_tolerance": side_effect_tolerance,
            },
            parent_cast_id=parent_cast_id,
            branch_id=branch_id,
        )
        print(format_cast_result(result))
        if fail_on_diverged:
            lin = result.get("lineage") or {}
            div = lin.get("divergence") or {}
            if str(div.get("status", "") or "") == "DIVERGED":
                raise SystemExit(2)
    except KeyError:
        pid = parent_cast_id or "parent"
        print(f"Cast not found: {pid}", file=sys.stderr)
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

