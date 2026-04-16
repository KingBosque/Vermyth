from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from vermyth.schema import BasisVersion


class BasisVersionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_basis_version(self, basis: BasisVersion) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO basis_versions (
                    version, dimensionality, aspect_order_json, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    int(basis.version),
                    int(basis.dimensionality),
                    json.dumps(list(basis.aspect_order)),
                    basis.created_at.isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_basis_version(self, version: int) -> BasisVersion:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM basis_versions WHERE version = ?", (int(version),))
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(version))
            return BasisVersion(
                version=int(row["version"]),
                dimensionality=int(row["dimensionality"]),
                aspect_order=json.loads(row["aspect_order_json"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_latest_basis_version(self) -> BasisVersion:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM basis_versions ORDER BY version DESC LIMIT 1")
            row = cur.fetchone()
            if row is None:
                return BasisVersion(
                    version=0,
                    dimensionality=6,
                    aspect_order=["VOID", "FORM", "MOTION", "MIND", "DECAY", "LIGHT"],
                )
            return BasisVersion(
                version=int(row["version"]),
                dimensionality=int(row["dimensionality"]),
                aspect_order=json.loads(row["aspect_order_json"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
