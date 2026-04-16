"""Policy decision persistence helpers."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from vermyth.schema import (
    DivergenceStatus,
    Intent,
    PolicyAction,
    PolicyDecision,
    PolicyThresholds,
)


class DecisionRepository:
    """Repository methods for policy decision persistence."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_policy_decision(self, decision: PolicyDecision) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO policy_decisions (
                    decision_id, action, cast_id, parent_cast_id, divergence_status,
                    narrative_coherence, thresholds_json, rationale, suggested_intent_json,
                    policy_model_name, policy_model_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.action.value,
                    decision.cast_id,
                    decision.parent_cast_id,
                    decision.divergence_status.value if decision.divergence_status else None,
                    float(decision.narrative_coherence)
                    if decision.narrative_coherence is not None
                    else None,
                    json.dumps(decision.thresholds.model_dump(mode="json")),
                    decision.rationale,
                    decision.suggested_intent.model_dump_json()
                    if decision.suggested_intent is not None
                    else None,
                    decision.model_name,
                    decision.model_version,
                    decision.timestamp.isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_policy_decision(self, decision_id: str) -> PolicyDecision:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM policy_decisions WHERE decision_id = ?",
                (str(decision_id),),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(decision_id))
            suggested = row["suggested_intent_json"]
            return PolicyDecision(
                decision_id=str(row["decision_id"]),
                action=PolicyAction(str(row["action"])),
                rationale=str(row["rationale"]),
                cast_id=str(row["cast_id"]),
                suggested_intent=Intent.model_validate_json(suggested)
                if suggested is not None
                else None,
                parent_cast_id=row["parent_cast_id"],
                divergence_status=(
                    DivergenceStatus(str(row["divergence_status"]))
                    if row["divergence_status"] is not None
                    else None
                ),
                narrative_coherence=(
                    float(row["narrative_coherence"])
                    if row["narrative_coherence"] is not None
                    else None
                ),
                thresholds=PolicyThresholds.model_validate(
                    json.loads(row["thresholds_json"])
                ),
                model_name=str(row["policy_model_name"]),
                model_version=(
                    str(row["policy_model_version"])
                    if row["policy_model_version"] is not None
                    else None
                ),
                timestamp=datetime.fromisoformat(str(row["created_at"])),
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_policy_decisions(
        self,
        action: PolicyAction | None = None,
        *,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[PolicyDecision]:
        try:
            cur = self._conn.cursor()
            where: list[str] = []
            params: list[Any] = []
            if action is not None:
                where.append("action = ?")
                params.append(action.value)
            if since is not None:
                where.append("created_at >= ?")
                params.append(since.isoformat())
            where_sql = ""
            if where:
                where_sql = "WHERE " + " AND ".join(where)
            params.append(int(limit))
            cur.execute(
                f"SELECT decision_id FROM policy_decisions {where_sql} ORDER BY created_at DESC LIMIT ?",
                tuple(params),
            )
            return [
                self.read_policy_decision(str(row["decision_id"]))
                for row in cur.fetchall()
            ]
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

