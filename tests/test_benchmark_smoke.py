from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from benchmarks.run import run_benchmark


def test_decide_benchmark_smoke() -> None:
    corpus = Path("benchmarks/corpus_v0_synthetic.json")
    assert corpus.exists()
    with TemporaryDirectory() as td:
        report = Path(td) / "report.md"
        result = run_benchmark(corpus, report, limit=6)
        assert report.exists()
    assert result["samples"] == 6
    assert float(result["macro_f1"]) >= 0.40
