from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from vermyth.schema import (
    CanonicalPacketV2,
    CanonicalResponseV2,
    SessionRecord,
    SessionStatus,
    SessionTransport,
)


class SessionRepository:
    """Repository methods for protocol session persistence."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_session(self, session: SessionRecord) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO sessions (
                    session_id, opened_at, closed_at, status, transport,
                    local_identity_json, remote_identity_json, capabilities_json,
                    last_sequence, anchor_cast_id, channel_branch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    opened_at=excluded.opened_at,
                    closed_at=excluded.closed_at,
                    status=excluded.status,
                    transport=excluded.transport,
                    local_identity_json=excluded.local_identity_json,
                    remote_identity_json=excluded.remote_identity_json,
                    capabilities_json=excluded.capabilities_json,
                    last_sequence=excluded.last_sequence,
                    anchor_cast_id=excluded.anchor_cast_id,
                    channel_branch_id=excluded.channel_branch_id
                """,
                (
                    session.session_id,
                    session.opened_at.isoformat(),
                    session.closed_at.isoformat() if session.closed_at is not None else None,
                    session.status.value,
                    session.transport.value,
                    json.dumps(session.local_identity.model_dump(mode="json")),
                    json.dumps(session.remote_identity.model_dump(mode="json")),
                    json.dumps(session.capabilities.model_dump(mode="json")),
                    int(session.last_sequence),
                    session.anchor_cast_id,
                    session.channel_branch_id,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_session(self, session_id: str) -> SessionRecord:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM sessions WHERE session_id = ?", (str(session_id),))
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(session_id))
            return SessionRecord(
                session_id=str(row["session_id"]),
                opened_at=datetime.fromisoformat(str(row["opened_at"])),
                closed_at=datetime.fromisoformat(str(row["closed_at"])) if row["closed_at"] is not None else None,
                status=SessionStatus(str(row["status"])),
                transport=SessionTransport(str(row["transport"])),
                local_identity=json.loads(row["local_identity_json"]),
                remote_identity=json.loads(row["remote_identity_json"]),
                capabilities=json.loads(row["capabilities_json"]),
                last_sequence=int(row["last_sequence"] or 0),
                anchor_cast_id=row["anchor_cast_id"],
                channel_branch_id=row["channel_branch_id"],
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def close_session(self, session_id: str) -> SessionRecord:
        s = self.read_session(session_id)
        closed = SessionRecord.model_construct(
            session_id=s.session_id,
            opened_at=s.opened_at,
            closed_at=datetime.now(timezone.utc),
            status=SessionStatus.CLOSED,
            transport=s.transport,
            local_identity=s.local_identity,
            remote_identity=s.remote_identity,
            capabilities=s.capabilities,
            last_sequence=s.last_sequence,
            anchor_cast_id=s.anchor_cast_id,
            channel_branch_id=s.channel_branch_id,
        )
        self.write_session(closed)
        return closed

    def advance_session_sequence(self, session_id: str, new_sequence: int) -> SessionRecord:
        s = self.read_session(session_id)
        if int(new_sequence) <= int(s.last_sequence):
            raise ValueError("new_sequence must be greater than last_sequence")
        advanced = SessionRecord.model_construct(
            session_id=s.session_id,
            opened_at=s.opened_at,
            closed_at=s.closed_at,
            status=s.status,
            transport=s.transport,
            local_identity=s.local_identity,
            remote_identity=s.remote_identity,
            capabilities=s.capabilities,
            last_sequence=int(new_sequence),
            anchor_cast_id=s.anchor_cast_id,
            channel_branch_id=s.channel_branch_id,
        )
        self.write_session(advanced)
        return advanced

    def write_session_packet(self, packet: CanonicalPacketV2) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO session_packets (
                    session_id, sequence, packet_type, payload_hash, payload_json, proof, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    packet.session_id,
                    int(packet.sequence),
                    packet.packet_type,
                    packet.payload_hash,
                    json.dumps(packet.payload),
                    packet.proof,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(str(exc)) from exc
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def write_session_response(self, response: CanonicalResponseV2) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO session_responses (
                    session_id, sequence, payload_hash, accepted, proof, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    response.session_id,
                    int(response.sequence),
                    response.payload_hash,
                    1 if response.accepted else 0,
                    response.proof,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(str(exc)) from exc
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_session_packets(self, session_id: str, limit: int) -> list[CanonicalPacketV2]:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT session_id, sequence, packet_type, payload_hash, payload_json, proof
                FROM session_packets
                WHERE session_id = ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (str(session_id), int(limit)),
            )
            out: list[CanonicalPacketV2] = []
            for row in cur.fetchall():
                out.append(
                    CanonicalPacketV2(
                        session_id=str(row["session_id"]),
                        sequence=int(row["sequence"]),
                        packet_type=str(row["packet_type"]),
                        payload_hash=str(row["payload_hash"]),
                        payload=json.loads(row["payload_json"]),
                        proof=str(row["proof"]),
                    )
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_session_responses(
        self, session_id: str, limit: int
    ) -> list[CanonicalResponseV2]:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT session_id, sequence, payload_hash, accepted, proof
                FROM session_responses
                WHERE session_id = ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (str(session_id), int(limit)),
            )
            out: list[CanonicalResponseV2] = []
            for row in cur.fetchall():
                out.append(
                    CanonicalResponseV2(
                        session_id=str(row["session_id"]),
                        sequence=int(row["sequence"]),
                        payload_hash=str(row["payload_hash"]),
                        accepted=bool(int(row["accepted"])),
                        proof=str(row["proof"]),
                    )
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
