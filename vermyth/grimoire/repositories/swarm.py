from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from vermyth.registry import AspectRegistry
from vermyth.schema import CrystallizedSigil, EmergentAspect, GossipPayload, GlyphSeed, SemanticVector, SwarmState, SwarmStatus


class SwarmRepository:
    """Repository methods for swarm state and gossip synchronization."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_swarm_state(self, state: SwarmState) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO swarms (
                    swarm_id, consensus_threshold, status, aggregated_vector_json,
                    last_cast_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(swarm_id) DO UPDATE SET
                    consensus_threshold=excluded.consensus_threshold,
                    status=excluded.status,
                    aggregated_vector_json=excluded.aggregated_vector_json,
                    last_cast_id=excluded.last_cast_id,
                    updated_at=excluded.updated_at
                """,
                (
                    state.swarm_id,
                    float(state.consensus_threshold),
                    state.status.value,
                    json.dumps(state.aggregated_vector.model_dump()),
                    state.last_cast_id,
                    state.updated_at.isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_swarm_state(self, swarm_id: str) -> SwarmState:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM swarms WHERE swarm_id = ?", (str(swarm_id),))
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(swarm_id))
            vec = SemanticVector.model_validate(json.loads(row["aggregated_vector_json"]))
            return SwarmState(
                swarm_id=str(row["swarm_id"]),
                consensus_threshold=float(row["consensus_threshold"]),
                status=SwarmStatus(str(row["status"])),
                aggregated_vector=vec,
                last_cast_id=row["last_cast_id"],
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def upsert_swarm_member(
        self,
        swarm_id: str,
        session_id: str,
        vector: SemanticVector,
        coherence_streak: int,
    ) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO swarm_members (swarm_id, session_id, vector_json, coherence_streak)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(swarm_id, session_id) DO UPDATE SET
                    vector_json=excluded.vector_json,
                    coherence_streak=excluded.coherence_streak
                """,
                (
                    str(swarm_id),
                    str(session_id),
                    json.dumps(vector.model_dump()),
                    int(coherence_streak),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_swarm_members(self, swarm_id: str) -> list[tuple[str, SemanticVector, int]]:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT session_id, vector_json, coherence_streak
                FROM swarm_members
                WHERE swarm_id = ?
                ORDER BY session_id ASC
                """,
                (str(swarm_id),),
            )
            out: list[tuple[str, SemanticVector, int]] = []
            for row in cur.fetchall():
                vec = SemanticVector.model_validate(json.loads(row["vector_json"]))
                out.append((str(row["session_id"]), vec, int(row["coherence_streak"])))
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def apply_gossip_sync(self, payload: GossipPayload, grimoire) -> dict[str, Any]:
        from vermyth.protocol.session_codec import verify_gossip_payload

        if not verify_gossip_payload(payload):
            raise ValueError("invalid gossip proof or federation secret not configured")
        merged_seeds = 0
        merged_crystals = 0
        for sd in payload.seeds:
            sd2 = dict(sd)
            sd2.pop("seed_id", None)
            if "aspect_pattern" in sd2 and sd2["aspect_pattern"] is not None:
                raw = sd2["aspect_pattern"]
                if isinstance(raw, list):
                    sd2["aspect_pattern"] = frozenset(
                        AspectRegistry.get().resolve(str(n)) for n in raw
                    )
            seed = GlyphSeed.model_validate(sd2)
            grimoire.write_seed(seed)
            merged_seeds += 1
        for cd in payload.crystallized:
            crystal = CrystallizedSigil.model_validate(cd)
            grimoire.write_crystallized_sigil(crystal)
            merged_crystals += 1
        merged_aspects = 0
        for ad in payload.emergent_aspects:
            aspect = EmergentAspect.model_validate(ad)
            grimoire.write_emergent_aspect(aspect)
            merged_aspects += 1
        return {
            "peer_id": payload.peer_id,
            "merged_seeds": merged_seeds,
            "merged_crystallized": merged_crystals,
            "merged_emergent_aspects": merged_aspects,
        }
