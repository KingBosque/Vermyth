from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmarks.run import _load_corpus, run_benchmark
from benchmarks.splits import sample_key, train_holdout_split
from benchmarks.tuner import tune_thresholds


def test_train_holdout_split_is_deterministic() -> None:
    corpus = _load_corpus(Path("benchmarks/corpus_v0_synthetic.json"))
    train_a, holdout_a = train_holdout_split(corpus)
    train_b, holdout_b = train_holdout_split(list(reversed(corpus)))
    assert [sample_key(row) for row in train_a] == [sample_key(row) for row in train_b]
    assert [sample_key(row) for row in holdout_a] == [sample_key(row) for row in holdout_b]


def test_tuner_non_regression_on_holdout() -> None:
    corpus = _load_corpus(Path("benchmarks/corpus_v0_synthetic.json"))
    train, holdout = train_holdout_split(corpus)
    with TemporaryDirectory() as td:
        root = Path(td)
        train_path = root / "train.json"
        holdout_path = root / "holdout.json"
        train_path.write_text(json.dumps(train), encoding="utf-8")
        holdout_path.write_text(json.dumps(holdout), encoding="utf-8")

        baseline_train = run_benchmark(train_path, root / "train_baseline.md")
        baseline_holdout = run_benchmark(holdout_path, root / "holdout_baseline.md")

        tuned = tune_thresholds(
            Path("benchmarks/corpus_v0_synthetic.json"),
            root / "tuned.json",
        )
        tuned_train = run_benchmark(
            train_path,
            root / "train_tuned.md",
            thresholds=tuned["thresholds"],
        )
        tuned_holdout = run_benchmark(
            holdout_path,
            root / "holdout_tuned.md",
            thresholds=tuned["thresholds"],
        )

    assert float(tuned_train["macro_f1"]) >= float(baseline_train["macro_f1"])
    assert float(tuned_holdout["macro_f1"]) + 0.02 >= float(baseline_holdout["macro_f1"])
