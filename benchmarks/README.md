# Benchmarks

- **Synthetic corpus** — fast regression; see `corpus_v0_synthetic.json` / `corpus_v1_synthetic.json`.
- **Dry-run adapters** — `adapters/osworld.py`, `adapters/webarena.py` (no full environment).
- **Real external** — `run_external.py`: outbound HTTP + `tool_decide`, writes JSON under `artifacts/`. Set `VERMYTH_BENCHMARK_EXTERNAL_URL` to target a specific URL.

Aggregated numbers and tiers live in `report.md`. Details: `docs/benchmarks.md`.
