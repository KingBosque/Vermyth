from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from vermyth.cli.format import format_arcane_transcript, format_cast_result

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_auto_cast(
    cli: "VermythCLI",
    vector: list[float],
    objective: str,
    scope: str,
    reversibility: str,
    side_effect_tolerance: str,
    *,
    max_depth: int = 5,
    target_resonance: float = 0.75,
    blend_alpha: float = 0.35,
    trace: bool = False,
    include_arcane_transcript: bool = False,
) -> None:
    try:
        result = cli._tools.tool_auto_cast(
            vector=vector,
            intent={
                "objective": objective,
                "scope": scope,
                "reversibility": reversibility,
                "side_effect_tolerance": side_effect_tolerance,
            },
            max_depth=max_depth,
            target_resonance=target_resonance,
            blend_alpha=blend_alpha,
            include_diagnostics=bool(trace),
            include_arcane_transcript=bool(include_arcane_transcript),
        )
        print(format_cast_result(result))
        chain = result.get("auto_cast_chain") or []
        print(f"Auto-cast depth: {result.get('auto_cast_depth', len(chain))}")
        if len(chain) > 1:
            print(f"Intermediate attempts: {len(chain) - 1}")
        if trace and result.get("diagnostics") is not None:
            diagnostics = result["diagnostics"]
            print("Diagnostics:")
            for idx, step in enumerate(diagnostics.get("steps", []), start=1):
                print(
                    f"  step {idx}: adjusted={float(step.get('adjusted', 0.0)):.4f}, "
                    f"raw={float(step.get('raw', 0.0)):.4f}, "
                    f"blend_alpha={float(step.get('blend_alpha', 0.0)):.4f}"
                )
            print(
                f"  converged={bool(diagnostics.get('converged', False))}, "
                f"final_adjusted={float(diagnostics.get('final_adjusted', 0.0)):.4f}"
            )
        if include_arcane_transcript and result.get("arcane_transcript") is not None:
            print()
            print(format_arcane_transcript(result["arcane_transcript"]))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ac = subs.add_parser("auto-cast", help="Self-healing fluid cast until coherent or max depth.")
    ac.add_argument("--vector", nargs="+", type=float, required=True, metavar="F")
    ac.add_argument("--objective", required=True, metavar="TEXT")
    ac.add_argument("--scope", required=True, metavar="TEXT")
    ac.add_argument(
        "--reversibility",
        required=True,
        choices=["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
    )
    ac.add_argument(
        "--side-effect-tolerance",
        required=True,
        choices=["NONE", "LOW", "MEDIUM", "HIGH"],
        dest="side_effect_tolerance",
    )
    ac.add_argument("--max-depth", type=int, default=5, dest="max_depth")
    ac.add_argument("--target-resonance", type=float, default=0.75, dest="target_resonance")
    ac.add_argument("--blend-alpha", type=float, default=0.35, dest="blend_alpha")
    ac.add_argument("--trace", action="store_true", default=False)
    ac.add_argument(
        "--arcane-transcript",
        action="store_true",
        default=False,
        help="Include presentation-only arcane transcript for the final cast (default off).",
    )


def _dispatch_auto_cast(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_auto_cast(
        vector=list(ns.vector),
        objective=ns.objective,
        scope=ns.scope,
        reversibility=ns.reversibility,
        side_effect_tolerance=ns.side_effect_tolerance,
        max_depth=int(ns.max_depth),
        target_resonance=float(ns.target_resonance),
        blend_alpha=float(ns.blend_alpha),
        trace=bool(ns.trace),
        include_arcane_transcript=bool(ns.arcane_transcript),
    )


DISPATCH = {"auto-cast": _dispatch_auto_cast}

