"""Deterministic genesis baseline: replay corpus through cast, then propose_genesis."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from vermyth.bootstrap import build_tools
from vermyth.schema import AspectID, Intent, ReversibilityClass, SideEffectTolerance

MIN_CLUSTER_SIZE = 15
MIN_UNEXPLAINED_VARIANCE = 0.3
MIN_COHERENCE_RATE = 0.6

CORPUS_REL = Path("benchmarks") / "corpus_v0_synthetic.json"
EXPECTED_REL = Path("benchmarks") / "fixtures" / "genesis_baseline_expected.json"
REPORT_REL = Path("benchmarks") / "genesis_report.md"


def load_corpus(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_cast_history(corpus: list[dict], *, db_path: Path) -> tuple[list, object]:
    grimoire, _composition, engine, _tools = build_tools(db_path=db_path)
    try:
        history = []
        for row in corpus:
            aspects = frozenset(AspectID[x] for x in row["aspects"])
            it = row["intent"]
            intent = Intent(
                objective=it["objective"],
                scope=it["scope"],
                reversibility=ReversibilityClass[it["reversibility"]],
                side_effect_tolerance=SideEffectTolerance[it["side_effect_tolerance"]],
            )
            history.append(engine.cast(aspects, intent))
        return history, engine
    finally:
        grimoire.close()


def run_baseline(
    *,
    corpus_path: Path,
) -> tuple[int, list[str]]:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        history, engine = build_cast_history(
            load_corpus(corpus_path),
            db_path=Path(td) / "genesis_baseline.db",
        )
    proposals = engine.propose_genesis(
        history,
        min_cluster_size=MIN_CLUSTER_SIZE,
        min_unexplained_variance=MIN_UNEXPLAINED_VARIANCE,
        min_coherence_rate=MIN_COHERENCE_RATE,
    )
    names = sorted(p.proposed_name for p in proposals)
    return len(proposals), names


def render_report(
    *,
    corpus_path: Path,
    proposal_count: int,
    proposal_names: list[str],
    updated: str,
) -> str:
    names_lines = "\n".join(f"  - `{n}`" for n in proposal_names) if proposal_names else "  - _(none)_"
    return (
        "# Genesis Regression Report\n\n"
        "This report records deterministic genesis proposal output for a fixed cast-history fixture.\n\n"
        "## Fixture\n\n"
        f"- source: `{corpus_path.as_posix()}`\n"
        "- mode: each sample is evaluated with `ResonanceEngine.cast`, then `propose_genesis`\n"
        "- thresholds:\n"
        f"  - min_cluster_size: {MIN_CLUSTER_SIZE}\n"
        f"  - min_unexplained_variance: {MIN_UNEXPLAINED_VARIANCE}\n"
        f"  - min_coherence_rate: {MIN_COHERENCE_RATE}\n\n"
        "## Baseline\n\n"
        f"- proposal_count: {proposal_count}\n"
        f"- proposal_names:\n{names_lines}\n"
        f"- reproducible_across_runs: yes (same corpus and thresholds)\n"
        f"- last_generated: {updated}\n"
        "- note: genesis remains experimental; see `docs/STABILITY.md`.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=_ROOT / CORPUS_REL,
    )
    parser.add_argument(
        "--expected",
        type=Path,
        default=_ROOT / EXPECTED_REL,
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_ROOT / REPORT_REL,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Recompute baseline and fail if it differs from --expected JSON.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Update --report (and --expected if used with regenerate flow).",
    )
    args = parser.parse_args()

    count, names = run_baseline(corpus_path=args.corpus)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    if args.check:
        exp = json.loads(args.expected.read_text(encoding="utf-8"))
        if int(exp["proposal_count"]) != count or list(exp["proposal_names"]) != names:
            raise SystemExit(
                f"genesis baseline drift: got count={count} names={names!r}, "
                f"expected count={exp['proposal_count']} names={exp['proposal_names']!r}"
            )
        print("genesis baseline check OK")
        return

    if args.write:
        try:
            corpus_display = args.corpus.relative_to(_ROOT)
        except ValueError:
            corpus_display = args.corpus
        args.report.write_text(
            render_report(
                corpus_path=corpus_display,
                proposal_count=count,
                proposal_names=names,
                updated=updated,
            ),
            encoding="utf-8",
        )
        args.expected.write_text(
            json.dumps({"proposal_count": count, "proposal_names": names}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {args.report} and {args.expected}")
        return

    print(json.dumps({"proposal_count": count, "proposal_names": names, "updated": updated}))


if __name__ == "__main__":
    main()
