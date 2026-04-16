# Decide gateway

`decide()` is Vermyth's policy gateway primitive. It produces an actionable decision
from a cast outcome:

- `ALLOW`
- `RESHAPE`
- `DENY`

## Inputs

- `intent` (required): objective, scope, reversibility, side effect tolerance.
- one of:
  - `aspects` for canonical cast-based decisioning
  - `vector` for fluid cast-based decisioning
  - neither, to auto-seed from the intent vector and run `auto_cast`
- optional `parent_cast_id` to include divergence policy checks
- optional `causal_root_cast_id` to include narrative coherence context
- optional `thresholds` to override policy defaults

## Policy defaults

`PolicyThresholds` defaults:

- `allow_min_resonance = 0.75`
- `reshape_min_resonance = 0.45`
- `max_drift_status = DRIFTING`

Decision mapping:

- `DENY`: incoherent verdict or diverged lineage.
- `ALLOW`: coherent verdict meeting allow threshold and drift policy.
- `RESHAPE`: all remaining states (typically partial coherence / drifting).

## CLI

```bash
vermyth decide \
  --aspects MIND LIGHT \
  --objective "Reveal hidden structure" \
  --scope "analysis" \
  --reversibility REVERSIBLE \
  --side-effect-tolerance LOW
```

## MCP

Use `tools/call` with `name: "decide"` and arguments:

```json
{
  "intent": {
    "objective": "Reveal hidden structure",
    "scope": "analysis",
    "reversibility": "REVERSIBLE",
    "side_effect_tolerance": "LOW"
  },
  "aspects": ["MIND", "LIGHT"]
}
```

## Benchmark workflow

Synthetic benchmark corpus lives at `benchmarks/corpus_v0_synthetic.json`.
An initial real corpus skeleton lives at `benchmarks/corpus_real.json`.
Each sample carries:

- `sample_id` (stable split key)
- `source` (`synthetic` or `real`)
- optional `disagreement: {reviewer, reason}` when the expected label is contested

Run:

```bash
python benchmarks/run.py
```

This writes `benchmarks/report.md` with macro-F1, ALLOW precision/recall, and
an expected->predicted confusion matrix.

For threshold tuning with an explicit train/holdout protocol:

```bash
python benchmarks/tuner.py
python benchmarks/run.py --tuned
```

The tuner writes `benchmarks/tuned_thresholds.json` and `--tuned` applies those
thresholds when producing the report.
