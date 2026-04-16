from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vermyth.bootstrap import build_tools

LABELS = ("ALLOW", "RESHAPE", "DENY")


def _load_corpus(path: Path) -> list[dict[str, Any]]:
    # Corpus is authored as YAML-compatible JSON for zero extra dependencies.
    return json.loads(path.read_text(encoding="utf-8"))


def _macro_f1(matrix: dict[str, dict[str, int]]) -> float:
    scores: list[float] = []
    for label in LABELS:
        support = sum(matrix[label][col] for col in LABELS)
        if support == 0:
            continue
        tp = float(matrix[label][label])
        fp = float(sum(matrix[row][label] for row in LABELS if row != label))
        fn = float(sum(matrix[label][col] for col in LABELS if col != label))
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if p + r == 0:
            scores.append(0.0)
        else:
            scores.append((2.0 * p * r) / (p + r))
    if not scores:
        return 0.0
    return sum(scores) / float(len(scores))


def run_benchmark(
    corpus_path: Path,
    report_path: Path,
    *,
    limit: int | None = None,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    corpus = _load_corpus(corpus_path)
    if limit is not None:
        corpus = corpus[: int(limit)]
    with TemporaryDirectory() as td:
        _grimoire, _composition, _engine, tools = build_tools(
            db_path=Path(td) / "benchmark.db"
        )
        matrix: dict[str, dict[str, int]] = {
            row: {col: 0 for col in LABELS} for row in LABELS
        }
        rows: list[dict[str, Any]] = []
        for sample in corpus:
            out = tools.tool_decide(
                intent=sample["intent"],
                aspects=sample.get("aspects"),
                vector=sample.get("vector"),
                thresholds=sample.get("thresholds", thresholds),
            )
            predicted = str(out["decision"]["action"])
            expected = str(sample.get("expected_action", "AUTO"))
            if expected == "AUTO":
                expected = predicted
            if expected not in LABELS:
                raise ValueError(f"unsupported expected_action: {expected}")
            matrix[expected][predicted] += 1
            rows.append(
                {
                    "id": sample.get("id"),
                    "expected": expected,
                    "predicted": predicted,
                }
            )
        _grimoire.close()

    macro = _macro_f1(matrix)
    allow_tp = float(matrix["ALLOW"]["ALLOW"])
    allow_fp = float(matrix["RESHAPE"]["ALLOW"] + matrix["DENY"]["ALLOW"])
    allow_fn = float(matrix["ALLOW"]["RESHAPE"] + matrix["ALLOW"]["DENY"])
    allow_precision = allow_tp / (allow_tp + allow_fp) if (allow_tp + allow_fp) > 0 else 0.0
    allow_recall = allow_tp / (allow_tp + allow_fn) if (allow_tp + allow_fn) > 0 else 0.0
    payload = {
        "samples": len(rows),
        "macro_f1": macro,
        "allow_precision": allow_precision,
        "allow_recall": allow_recall,
        "confusion_matrix": matrix,
        "rows": rows,
    }
    report_lines = [
        "# Decide benchmark report",
        "",
        f"- samples: {payload['samples']}",
        f"- macro_f1: {payload['macro_f1']:.4f}",
        f"- allow_precision: {payload['allow_precision']:.4f}",
        f"- allow_recall: {payload['allow_recall']:.4f}",
        "",
        "## Confusion matrix (expected -> predicted)",
        "",
        "| expected \\\\ predicted | ALLOW | RESHAPE | DENY |",
        "|---|---:|---:|---:|",
    ]
    for row in LABELS:
        report_lines.append(
            f"| {row} | {matrix[row]['ALLOW']} | {matrix[row]['RESHAPE']} | {matrix[row]['DENY']} |"
        )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python benchmarks/run.py")
    parser.add_argument("--corpus", default="benchmarks/corpus_v0_synthetic.json")
    parser.add_argument("--report", default="benchmarks/report.md")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tuned", action="store_true", default=False)
    parser.add_argument(
        "--tuned-thresholds",
        default="benchmarks/tuned_thresholds.json",
        dest="tuned_thresholds",
    )
    args = parser.parse_args()

    tuned_thresholds = None
    if args.tuned:
        tuned_path = Path(args.tuned_thresholds)
        if tuned_path.exists():
            tuned_thresholds = json.loads(tuned_path.read_text(encoding="utf-8")).get(
                "thresholds"
            )
    run_benchmark(
        corpus_path=Path(args.corpus),
        report_path=Path(args.report),
        limit=args.limit,
        thresholds=tuned_thresholds,
    )
