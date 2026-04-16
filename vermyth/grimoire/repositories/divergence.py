from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from vermyth.schema import (
    DivergenceReport,
    DivergenceStatus,
    DivergenceThresholds,
    DivergenceThresholds_DEFAULT,
)


class DivergenceRepository:
    """Repository methods for divergence persistence."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_divergence_report(self, report: DivergenceReport) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO divergence_reports (
                    cast_id, parent_cast_id, l2_magnitude, cosine_distance, status, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report.cast_id,
                    report.parent_cast_id,
                    float(report.l2_magnitude),
                    float(report.cosine_distance),
                    report.status.name,
                    report.computed_at.isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_divergence_report(self, cast_id: str) -> DivergenceReport:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM divergence_reports WHERE cast_id = ?", (cast_id,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(cast_id)
            return DivergenceReport(
                cast_id=row["cast_id"],
                parent_cast_id=row["parent_cast_id"],
                l2_magnitude=float(row["l2_magnitude"]),
                cosine_distance=float(row["cosine_distance"]),
                status=DivergenceStatus[row["status"]],
                computed_at=datetime.fromisoformat(row["computed_at"]),
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_divergence_reports(
        self,
        status: DivergenceStatus | None = None,
        limit: int = 50,
        *,
        since: datetime | None = None,
    ) -> list[DivergenceReport]:
        try:
            cur = self._conn.cursor()
            where: list[str] = []
            params: list[object] = []
            if status is not None:
                where.append("status = ?")
                params.append(status.name)
            if since is not None:
                where.append("computed_at >= ?")
                params.append(since.isoformat())
            where_sql = ""
            if where:
                where_sql = "WHERE " + " AND ".join(where)
            params.append(int(limit))
            cur.execute(
                f"SELECT * FROM divergence_reports {where_sql} ORDER BY computed_at DESC LIMIT ?",
                tuple(params),
            )
            out: list[DivergenceReport] = []
            for row in cur.fetchall():
                out.append(
                    DivergenceReport(
                        cast_id=row["cast_id"],
                        parent_cast_id=row["parent_cast_id"],
                        l2_magnitude=float(row["l2_magnitude"]),
                        cosine_distance=float(row["cosine_distance"]),
                        status=DivergenceStatus[row["status"]],
                        computed_at=datetime.fromisoformat(row["computed_at"]),
                    )
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def write_divergence_thresholds(self, thresholds: DivergenceThresholds) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO divergence_thresholds (
                    id, l2_stable_max, l2_diverged_min, cosine_stable_max, cosine_diverged_min, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?)
                """,
                (
                    float(thresholds.l2_stable_max),
                    float(thresholds.l2_diverged_min),
                    float(thresholds.cosine_stable_max),
                    float(thresholds.cosine_diverged_min),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_divergence_thresholds(self) -> DivergenceThresholds:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM divergence_thresholds WHERE id = 1")
            row = cur.fetchone()
            if row is None:
                return DivergenceThresholds_DEFAULT
            return DivergenceThresholds(
                l2_stable_max=float(row["l2_stable_max"]),
                l2_diverged_min=float(row["l2_diverged_min"]),
                cosine_stable_max=float(row["cosine_stable_max"]),
                cosine_diverged_min=float(row["cosine_diverged_min"]),
            )
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def drift_branches(self, limit: int = 25) -> list[dict[str, Any]]:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
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
                """,
                (int(limit),),
            )
            out: list[dict[str, Any]] = []
            for row in cur.fetchall():
                out.append(
                    {
                        "branch_id": row["branch_id"],
                        "casts_with_divergence": int(row["casts_with_divergence"] or 0),
                        "diverged_count": int(row["diverged_count"] or 0),
                        "drifting_count": int(row["drifting_count"] or 0),
                        "max_l2": float(row["max_l2"] or 0.0),
                        "max_cosine_distance": float(row["max_cosine_distance"] or 0.0),
                        "latest_computed_at": row["latest_computed_at"],
                    }
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def cast_pairs_missing_divergence_reports(
        self, limit: int = 500
    ) -> list[tuple[str, str]]:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT
                    cr.cast_id AS cast_id,
                    json_extract(cr.lineage_json, '$.parent_cast_id') AS parent_cast_id
                FROM cast_results cr
                LEFT JOIN divergence_reports dr ON dr.cast_id = cr.cast_id
                WHERE cr.lineage_json IS NOT NULL
                  AND dr.cast_id IS NULL
                ORDER BY cr.timestamp DESC
                LIMIT ?
                """,
                (int(limit),),
            )
            out: list[tuple[str, str]] = []
            for row in cur.fetchall():
                cid = str(row["cast_id"])
                pid = row["parent_cast_id"]
                if pid is None:
                    continue
                out.append((cid, str(pid)))
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
