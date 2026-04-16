## Drift playbook

This document explains how to interpret and use Vermyth’s drift (divergence) observability features.

### Terms
- **Divergence**: semantic drift between a child cast’s sigil vector and its parent cast’s sigil vector.
- **DivergenceReport**: persisted record of drift metrics and classification for a cast.
- **Status**:
  - **STABLE**: below stable thresholds
  - **DRIFTING**: between stable and diverged thresholds
  - **DIVERGED**: exceeds diverged threshold(s)

### Metrics
- **L2 magnitude**: \(\\| child - parent \\|_2\\) computed in semantic component space.
- **Cosine distance**: \(1 - \\cos(\\theta)\\) between parent and child semantic vectors.

Status is chosen as the **worst** (most severe) of the L2 and cosine distance classifications.

### CLI workflows

#### 1) Inspect a cast’s divergence

```bash
vermyth divergence CAST_ID
```

#### 2) List recent divergence reports

```bash
vermyth divergences --status DIVERGED --limit 50
```

Filter by time (ISO datetime):

```bash
vermyth divergences --since 2026-04-01T00:00:00+00:00
```

#### 3) Rank branches by drift severity

```bash
vermyth drift-branches --limit 25
```

#### 4) Summarize drift across a lineage chain

```bash
vermyth lineage-drift CAST_ID --max-depth 50 --top-k 3
```

#### 5) Fail-fast on diverged casts (automation)

When casting with a parent, exit code 2 indicates the new cast is **DIVERGED** from its parent.

```bash
vermyth cast --aspects MIND LIGHT --objective \"study\" --scope local --reversibility REVERSIBLE --side-effect-tolerance HIGH --parent PARENT_CAST_ID --fail-on-diverged
```

#### 6) Backfill missing divergence reports

If you added divergence after some casts already existed, you can backfill persisted reports:

```bash
vermyth backfill-divergence --limit 500
```

### MCP workflows

- `divergence_thresholds`: read active thresholds
- `set_divergence_thresholds`: update thresholds
- `divergence_reports`: list persisted reports
- `drift_branches`: branch leaderboard
- `lineage_drift`: lineage drift summary
### Tuning thresholds

Use the thresholds command to inspect current values:

```bash
vermyth thresholds
```

Update values:

```bash
vermyth set-thresholds --l2-stable 0.25 --l2-diverged 0.60 --cosine-stable 0.15 --cosine-diverged 0.45
```

