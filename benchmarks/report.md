# Benchmark Report

This report has two tiers:

- Regression fixture (synthetic): fast stability checks for internal policy behavior.
- External task evaluation (dry run): adapter-level checks for OSWorld/WebArena-style tasks.

## Regression fixture (synthetic)

- corpus: `benchmarks/corpus_v0_synthetic.json`
- samples: 60
- macro_f1: 1.0000
- allow_precision: 1.0000
- allow_recall: 1.0000

### Confusion matrix (expected -> predicted)

| expected \\ predicted | ALLOW | RESHAPE | DENY |
|---|---:|---:|---:|
| ALLOW | 15 | 0 | 0 |
| RESHAPE | 0 | 20 | 0 |
| DENY | 0 | 0 | 25 |

## External task evaluation (dry run)

- **osworld**: success_rate=0.5000; reshape_rate=0.5000; samples=2 (updated 2026-04-16T21:50Z)
- **webarena**: success_rate=0.5000; reshape_rate=0.5000; samples=2 (updated 2026-04-16T21:50Z)
- note: adapter-level checks only; not equivalent to full live-environment benchmark runs.

