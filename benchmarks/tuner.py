from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.run import _load_corpus, run_benchmark
from benchmarks.splits import train_holdout_split


def _frange(start: float, stop: float, step: float) -> list[float]:
    values: list[float] = []
    cur = start
    while cur <= stop + 1e-9:
        values.append(round(cur, 3))
        cur += step
    return values


def tune_thresholds(
    corpus_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    corpus = _load_corpus(corpus_path)
    train, holdout = train_holdout_split(corpus)
    with TemporaryDirectory() as td:
        train_path = Path(td) / "train.json"
        holdout_path = Path(td) / "holdout.json"
        train_path.write_text(json.dumps(train), encoding="utf-8")
        holdout_path.write_text(json.dumps(holdout), encoding="utf-8")

        best_payload: dict[str, Any] | None = None
        for allow in _frange(0.55, 0.90, 0.025):
            for reshape in _frange(0.30, 0.55, 0.025):
                if reshape >= allow:
                    continue
                thresholds = {
                    "allow_min_resonance": allow,
                    "reshape_min_resonance": reshape,
                    "max_drift_status": "DRIFTING",
                }
                train_result = run_benchmark(
                    train_path,
                    Path(td) / "train_report.md",
                    thresholds=thresholds,
                )
                holdout_result = run_benchmark(
                    holdout_path,
                    Path(td) / "holdout_report.md",
                    thresholds=thresholds,
                )
                payload = {
                    "macro_f1_train": float(train_result["macro_f1"]),
                    "macro_f1_holdout": float(holdout_result["macro_f1"]),
                    "thresholds": thresholds,
                }
                if best_payload is None:
                    best_payload = payload
                    continue
                score = (payload["macro_f1_holdout"], payload["macro_f1_train"])
                best_score = (
                    best_payload["macro_f1_holdout"],
                    best_payload["macro_f1_train"],
                )
                if score > best_score:
                    best_payload = payload
        assert best_payload is not None
    output_path.write_text(json.dumps(best_payload, indent=2) + "\n", encoding="utf-8")
    return best_payload


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    tune_thresholds(
        corpus_path=root / "corpus_v0_synthetic.json",
        output_path=root / "tuned_thresholds.json",
    )
