from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from vermyth.registry import AspectRegistry
from vermyth.schema import RegisteredAspect


class RegistryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_registered_aspect(self, aspect: RegisteredAspect, ordinal: int) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT COALESCE(MAX(version), 0) AS version FROM basis_versions")
            row = cur.fetchone()
            latest_version = int(row["version"]) if row is not None else 0
            next_basis = latest_version + 1
            cur.execute(
                """
                INSERT INTO registered_aspects (
                    name, polarity, entropy_coefficient, symbol, ordinal, registered_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    aspect.name,
                    int(aspect.polarity),
                    float(aspect.entropy_coefficient),
                    aspect.symbol,
                    int(ordinal),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            cur.execute(
                """
                INSERT OR REPLACE INTO basis_versions (
                    version, dimensionality, aspect_order_json, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    int(next_basis),
                    int(ordinal) + 1,
                    json.dumps([a.name for a in AspectRegistry.get().full_order]),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()
            AspectRegistry.get().set_basis_version(next_basis)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Aspect {aspect.name!r} already exists") from exc
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_registered_aspects(self) -> list[tuple[RegisteredAspect, int]]:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT name, polarity, entropy_coefficient, symbol, ordinal FROM registered_aspects ORDER BY ordinal ASC"
            )
            out: list[tuple[RegisteredAspect, int]] = []
            for row in cur.fetchall():
                aspect = RegisteredAspect(
                    name=row["name"],
                    polarity=int(row["polarity"]),
                    entropy_coefficient=float(row["entropy_coefficient"]),
                    symbol=row["symbol"],
                )
                out.append((aspect, int(row["ordinal"])))
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def write_registered_sigil(
        self,
        name: str,
        aspects: list[str],
        effect_class: str,
        resonance_ceiling: float,
        contradiction_severity: str,
        is_override: bool,
    ) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO registered_sigils (
                    name, aspects_json, effect_class, resonance_ceiling,
                    contradiction_severity, is_override, registered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    json.dumps(aspects),
                    effect_class,
                    float(resonance_ceiling),
                    contradiction_severity,
                    1 if is_override else 0,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_registered_sigil(self, name: str) -> dict:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM registered_sigils WHERE name = ?", (name,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(name)
            return {
                "name": row["name"],
                "aspects": json.loads(row["aspects_json"]),
                "effect_class": row["effect_class"],
                "resonance_ceiling": float(row["resonance_ceiling"]),
                "contradiction_severity": row["contradiction_severity"],
                "is_override": bool(row["is_override"]),
            }
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_registered_sigils(self) -> list[dict]:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM registered_sigils ORDER BY registered_at DESC")
            out: list[dict] = []
            for row in cur.fetchall():
                out.append(
                    {
                        "name": row["name"],
                        "aspects": json.loads(row["aspects_json"]),
                        "effect_class": row["effect_class"],
                        "resonance_ceiling": float(row["resonance_ceiling"]),
                        "contradiction_severity": row["contradiction_severity"],
                        "is_override": bool(row["is_override"]),
                    }
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
