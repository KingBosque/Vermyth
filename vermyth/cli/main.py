"""Vermyth CLI: human-readable inspection and debugging."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from vermyth.contracts import CLIContract
from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.cli.format import (
    format_cast_result,
    format_cast_table,
    format_search_table,
    format_seed_table,
)
from vermyth.mcp.tools import VermythTools


class VermythCLI(CLIContract):
    """Command-line interface over VermythTools."""

    def __init__(
        self,
        engine: ResonanceEngine | None = None,
        grimoire: Grimoire | None = None,
    ) -> None:
        if engine is not None and grimoire is not None:
            self._engine = engine
            self._grimoire = grimoire
        else:
            composition = CompositionEngine()
            self._grimoire = Grimoire()
            self._engine = ResonanceEngine(
                composition_engine=composition, backend=None
            )
        self._tools = VermythTools(self._engine, self._grimoire)

    def cmd_cast(
        self,
        aspects: list[str],
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
    ) -> None:
        try:
            result = self._tools.tool_cast(
                aspects=aspects,
                intent={
                    "objective": objective,
                    "scope": scope,
                    "reversibility": reversibility,
                    "side_effect_tolerance": side_effect_tolerance,
                },
            )
            print(format_cast_result(result))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            if (
                type(e).__name__ == "ValidationError"
                and type(e).__module__.startswith("pydantic")
            ):
                print(str(e), file=sys.stderr)
                sys.exit(1)
            raise

    def cmd_query(
        self,
        verdict: Optional[str],
        min_resonance: Optional[float],
        branch_id: Optional[str],
        limit: int,
    ) -> None:
        try:
            filters: dict = {"limit": limit}
            if verdict is not None:
                filters["verdict_filter"] = verdict
            if min_resonance is not None:
                filters["min_resonance"] = min_resonance
            if branch_id is not None:
                filters["branch_id"] = branch_id
            results = self._tools.tool_query(filters)
            print(format_cast_table(results))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            if (
                type(e).__name__ == "ValidationError"
                and type(e).__module__.startswith("pydantic")
            ):
                print(str(e), file=sys.stderr)
                sys.exit(1)
            raise

    def cmd_search(self, vector: list[float], threshold: float, limit: int) -> None:
        try:
            results = self._tools.tool_semantic_search(
                proximity_vector=vector,
                threshold=threshold,
                limit=limit,
            )
            print(format_search_table(results, similarities=None))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    def cmd_inspect(self, cast_id: str) -> None:
        try:
            result = self._tools.tool_inspect(cast_id=cast_id)
            print(format_cast_result(result))
        except KeyError:
            print(f"Cast not found: {cast_id}", file=sys.stderr)
            sys.exit(1)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    def cmd_seeds(self, crystallized: Optional[bool]) -> None:
        try:
            results = self._tools.tool_seeds(crystallized=crystallized)
            print(format_seed_table(results))
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    def build_parser(self) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser(
            prog="vermyth",
            description="Vermyth — semantic execution language for AI systems.",
        )
        subs = p.add_subparsers(dest="command", required=True)

        c = subs.add_parser("cast", help="Cast aspects with an intent.")
        c.add_argument(
            "--aspects",
            nargs="+",
            required=True,
            metavar="ASPECT",
            help="One to three aspect names. Valid: VOID FORM MOTION MIND DECAY LIGHT.",
        )
        c.add_argument(
            "--objective",
            required=True,
            metavar="TEXT",
            help="What this casting should accomplish. Max 500 chars.",
        )
        c.add_argument(
            "--scope",
            required=True,
            metavar="TEXT",
            help="Bounded domain this casting applies to. Max 200 chars.",
        )
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

        q = subs.add_parser("query", help="Query stored casts.")
        q.add_argument(
            "--verdict",
            choices=["COHERENT", "PARTIAL", "INCOHERENT"],
            default=None,
        )
        q.add_argument(
            "--min-resonance",
            type=float,
            default=None,
            dest="min_resonance",
        )
        q.add_argument("--branch-id", default=None, dest="branch_id")
        q.add_argument("--limit", type=int, default=20)

        s = subs.add_parser("search", help="Semantic search over casts.")
        s.add_argument(
            "--vector",
            nargs=6,
            type=float,
            required=True,
            metavar="F",
            help="Six floats in canonical aspect order: VOID FORM MOTION MIND DECAY LIGHT.",
        )
        s.add_argument("--threshold", type=float, required=True)
        s.add_argument("--limit", type=int, default=20)

        i = subs.add_parser("inspect", help="Inspect one cast by id.")
        i.add_argument("cast_id", metavar="CAST_ID")

        sd = subs.add_parser("seeds", help="List glyph seeds.")
        sd.add_argument(
            "--crystallized",
            action="store_true",
            default=None,
            help="Show only crystallized seeds.",
        )
        sd.add_argument(
            "--accumulating",
            action="store_true",
            default=None,
            help="Show only accumulating seeds.",
        )
        return p

    def run(self, args: list[str] | None = None) -> None:
        ns = self.build_parser().parse_args(args)
        if ns.command == "cast":
            self.cmd_cast(
                aspects=ns.aspects,
                objective=ns.objective,
                scope=ns.scope,
                reversibility=ns.reversibility,
                side_effect_tolerance=ns.side_effect_tolerance,
            )
        elif ns.command == "query":
            self.cmd_query(
                verdict=ns.verdict,
                min_resonance=ns.min_resonance,
                branch_id=ns.branch_id,
                limit=ns.limit,
            )
        elif ns.command == "search":
            self.cmd_search(
                vector=list(ns.vector),
                threshold=ns.threshold,
                limit=ns.limit,
            )
        elif ns.command == "inspect":
            self.cmd_inspect(cast_id=ns.cast_id)
        elif ns.command == "seeds":
            if ns.crystallized:
                self.cmd_seeds(crystallized=True)
            elif ns.accumulating:
                self.cmd_seeds(crystallized=False)
            else:
                self.cmd_seeds(crystallized=None)
        else:
            raise SystemExit(2)


def main() -> None:
    VermythCLI().run()


if __name__ == "__main__":
    main()
