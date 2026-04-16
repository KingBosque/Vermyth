from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from vermyth.schema import (
    ChannelState,
    ChannelStatus,
    SemanticVector,
    VerdictType,
    current_basis_version,
)


class ChannelRepository:
    """Repository methods for channel state persistence."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_channel_state(self, state: ChannelState) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO channel_states (
                    branch_id,
                    cast_count,
                    cumulative_resonance,
                    mean_resonance,
                    coherence_streak,
                    last_verdict_type,
                    status,
                    last_cast_id,
                    constraint_vector_json,
                    updated_at,
                    basis_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(branch_id) DO UPDATE SET
                    cast_count=excluded.cast_count,
                    cumulative_resonance=excluded.cumulative_resonance,
                    mean_resonance=excluded.mean_resonance,
                    coherence_streak=excluded.coherence_streak,
                    last_verdict_type=excluded.last_verdict_type,
                    status=excluded.status,
                    last_cast_id=excluded.last_cast_id,
                    constraint_vector_json=excluded.constraint_vector_json,
                    updated_at=excluded.updated_at,
                    basis_version=excluded.basis_version
                """,
                (
                    state.branch_id,
                    int(state.cast_count),
                    float(state.cumulative_resonance),
                    float(state.mean_resonance),
                    int(state.coherence_streak),
                    state.last_verdict_type.name,
                    state.status.name,
                    state.last_cast_id,
                    json.dumps(list(state.constraint_vector.components))
                    if state.constraint_vector is not None
                    else None,
                    state.updated_at.isoformat(),
                    (
                        state.constraint_vector.normalized_basis_version()
                        if state.constraint_vector is not None
                        else current_basis_version()
                    ),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_channel_state(self, branch_id: str) -> ChannelState:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM channel_states WHERE branch_id = ?",
                (str(branch_id),),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(branch_id))
            constraint = row["constraint_vector_json"]
            constraint_vec = None
            if constraint is not None:
                comps = json.loads(constraint)
                basis = (
                    int(row["basis_version"])
                    if "basis_version" in row.keys() and row["basis_version"] is not None
                    else 0
                )
                constraint_vec = SemanticVector(
                    components=tuple(float(x) for x in comps),
                    basis_version=basis,
                )
            return ChannelState(
                branch_id=str(row["branch_id"]),
                cast_count=int(row["cast_count"]),
                cumulative_resonance=float(row["cumulative_resonance"]),
                mean_resonance=float(row["mean_resonance"]),
                coherence_streak=int(row["coherence_streak"]),
                last_verdict_type=VerdictType[str(row["last_verdict_type"])],
                status=ChannelStatus[str(row["status"])],
                last_cast_id=str(row["last_cast_id"]),
                constraint_vector=constraint_vec,
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_channel_states(
        self, status: Optional[str], limit: int
    ) -> list[ChannelState]:
        try:
            cur = self._conn.cursor()
            params: list[Any] = []
            where = ""
            if status is not None:
                where = "WHERE status = ?"
                params.append(str(status))
            params.append(int(limit))
            cur.execute(
                f"SELECT * FROM channel_states {where} ORDER BY updated_at DESC LIMIT ?",
                tuple(params),
            )
            out: list[ChannelState] = []
            for row in cur.fetchall():
                constraint = row["constraint_vector_json"]
                constraint_vec = None
                if constraint is not None:
                    comps = json.loads(constraint)
                    basis = (
                        int(row["basis_version"])
                        if "basis_version" in row.keys() and row["basis_version"] is not None
                        else 0
                    )
                    constraint_vec = SemanticVector(
                        components=tuple(float(x) for x in comps),
                        basis_version=basis,
                    )
                out.append(
                    ChannelState(
                        branch_id=str(row["branch_id"]),
                        cast_count=int(row["cast_count"]),
                        cumulative_resonance=float(row["cumulative_resonance"]),
                        mean_resonance=float(row["mean_resonance"]),
                        coherence_streak=int(row["coherence_streak"]),
                        last_verdict_type=VerdictType[str(row["last_verdict_type"])],
                        status=ChannelStatus[str(row["status"])],
                        last_cast_id=str(row["last_cast_id"]),
                        constraint_vector=constraint_vec,
                        updated_at=datetime.fromisoformat(str(row["updated_at"])),
                    )
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
