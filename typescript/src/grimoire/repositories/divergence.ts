import BetterSqlite3 from "better-sqlite3";

import {
  defaultDivergenceThresholds,
  type DivergenceReport,
  type DivergenceThresholds,
} from "../../schema/divergence.js";
import type { DivergenceStatus } from "../../schema/enums.js";

type SqliteDb = InstanceType<typeof BetterSqlite3>;

export class DivergenceRepository {
  constructor(private readonly db: SqliteDb) {}

  readDivergenceThresholds(): DivergenceThresholds {
    const row = this.db
      .prepare("SELECT * FROM divergence_thresholds WHERE id = 1")
      .get() as
      | {
          l2_stable_max: number;
          l2_diverged_min: number;
          cosine_stable_max: number;
          cosine_diverged_min: number;
        }
      | undefined;
    if (!row) {
      return defaultDivergenceThresholds();
    }
    return {
      l2StableMax: Number(row.l2_stable_max),
      l2DivergedMin: Number(row.l2_diverged_min),
      cosineStableMax: Number(row.cosine_stable_max),
      cosineDivergedMin: Number(row.cosine_diverged_min),
    };
  }

  readDivergenceReport(castId: string): DivergenceReport | null {
    const row = this.db.prepare("SELECT * FROM divergence_reports WHERE cast_id = ?").get(castId) as
      | {
          cast_id: string;
          parent_cast_id: string;
          l2_magnitude: number;
          cosine_distance: number;
          status: string;
          computed_at: string;
        }
      | undefined;
    if (!row) {
      return null;
    }
    return {
      castId: String(row.cast_id),
      parentCastId: String(row.parent_cast_id),
      l2Magnitude: Number(row.l2_magnitude),
      cosineDistance: Number(row.cosine_distance),
      status: row.status as DivergenceStatus,
      computedAt: new Date(String(row.computed_at)),
      basisNote: null,
    };
  }

  driftBranches(limit: number): Array<Record<string, unknown>> {
    const rows = this.db
      .prepare(
        `
      SELECT
        cr.branch_id AS branch_id,
        COUNT(*) AS casts_with_divergence,
        SUM(CASE WHEN dr.status = 'DIVERGED' THEN 1 ELSE 0 END) AS diverged_count,
        SUM(CASE WHEN dr.status = 'DRIFTING' THEN 1 ELSE 0 END) AS drifting_count,
        MAX(dr.l2_magnitude) AS max_l2,
        MAX(dr.cosine_distance) AS max_cosine_distance,
        MAX(dr.computed_at) AS latest_computed_at
      FROM divergence_reports dr
      JOIN cast_results cr ON cr.cast_id = dr.cast_id
      WHERE cr.branch_id IS NOT NULL
      GROUP BY cr.branch_id
      ORDER BY
        diverged_count DESC,
        drifting_count DESC,
        max_l2 DESC,
        max_cosine_distance DESC,
        latest_computed_at DESC
      LIMIT ?
    `,
      )
      .all(Math.max(1, Math.min(500, Math.floor(limit)))) as Array<{
      branch_id: string;
      casts_with_divergence: number;
      diverged_count: number;
      drifting_count: number;
      max_l2: number;
      max_cosine_distance: number;
      latest_computed_at: string;
    }>;
    return rows.map((row) => ({
      branch_id: row.branch_id,
      casts_with_divergence: Number(row.casts_with_divergence ?? 0),
      diverged_count: Number(row.diverged_count ?? 0),
      drifting_count: Number(row.drifting_count ?? 0),
      max_l2: Number(row.max_l2 ?? 0),
      max_cosine_distance: Number(row.max_cosine_distance ?? 0),
      latest_computed_at: row.latest_computed_at,
    }));
  }
}
