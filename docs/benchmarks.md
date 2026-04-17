# Benchmarks

Vermyth separates **fast synthetic regression** from **optional real external** runs.

## Synthetic regression

- Fixture: `benchmarks/corpus_v0_synthetic.json` (or `corpus_v1_synthetic.json` if present).
- Purpose: policy/decision behavior stability, not frontier performance claims.
- Run via your existing benchmark driver (see `benchmarks/`).

## Dry-run external adapters

- `benchmarks/adapters/osworld.py`, `benchmarks/adapters/webarena.py` — task-shaped loops without requiring full upstream environments.
- Labeled as **dry-run** in `benchmarks/report.md`.

## Real external path (network + artifacts)

- Script: `benchmarks/run_external.py` (or `python -m` equivalent).
- Performs an outbound HTTP fetch and a `tool_decide` call; writes JSON under `benchmarks/artifacts/`.
- **Environment:** `VERMYTH_BENCHMARK_EXTERNAL_URL` overrides the default URL (`https://example.com` if unset).
- **Optional extra:** `bench-real` is reserved in `pyproject.toml` for future pinned drivers (OSWorld/WebArena); not required for the urllib-based harness.

## Pytest

Tests that depend on large external assets should **skip** when drivers are missing (`pytest.importorskip` or a clear env gate).

## Reporting

See `benchmarks/report.md` for **Synthetic regression** vs **External task evaluation (dry run)** vs **Real external** sections.
