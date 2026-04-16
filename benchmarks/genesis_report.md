# Genesis Regression Report

This report records deterministic genesis proposal output for a fixed cast-history fixture.

## Fixture

- source: `benchmarks/corpus_v0_synthetic.json`
- mode: each sample is evaluated with `ResonanceEngine.cast`, then `propose_genesis`
- thresholds:
  - min_cluster_size: 15
  - min_unexplained_variance: 0.3
  - min_coherence_rate: 0.6

## Baseline

- proposal_count: 0
- proposal_names:
  - _(none)_
- reproducible_across_runs: yes (same corpus and thresholds)
- last_generated: 2026-04-16T21:51Z
- note: genesis remains experimental; see `docs/STABILITY.md`.
