from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from vermyth.registry import AspectRegistry
from vermyth.schema import (
    Aspect,
    ContradictionSeverity,
    CrystallizedSigil,
    EffectClass,
    Polarity,
    SemanticVector,
    Sigil,
)


class CrystallizedRepository:
    """Repository methods for crystallized sigil persistence."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def _serialize_crystallized_sigil(self, crystal: CrystallizedSigil) -> dict:
        return {
            "name": crystal.name,
            "sigil_json": json.dumps(
                {
                    "name": crystal.sigil.name,
                    "aspects": [a.name for a in crystal.sigil.aspects],
                    "effect_class": crystal.sigil.effect_class.name,
                    "resonance_ceiling": crystal.sigil.resonance_ceiling,
                    "contradiction_severity": crystal.sigil.contradiction_severity.name,
                    "semantic_fingerprint": crystal.sigil.semantic_fingerprint,
                    "semantic_vector": list(crystal.sigil.semantic_vector.components),
                    "polarity": crystal.sigil.polarity.name,
                }
            ),
            "source_seed_id": crystal.source_seed_id,
            "crystallized_at": crystal.crystallized_at.isoformat(),
            "generation": int(crystal.generation),
            "aspect_pattern_json": json.dumps([a.name for a in crystal.sigil.aspects]),
            "basis_version": crystal.sigil.semantic_vector.normalized_basis_version(),
        }

    def _deserialize_crystallized_sigil(self, row: sqlite3.Row) -> CrystallizedSigil:
        sigil_d = json.loads(row["sigil_json"])
        aspects = frozenset(AspectRegistry.get().resolve(n) for n in sigil_d["aspects"])
        basis_version = (
            int(row["basis_version"])
            if "basis_version" in row.keys() and row["basis_version"] is not None
            else 0
        )
        sigil = Sigil.model_construct(
            name=sigil_d["name"],
            aspects=aspects,
            effect_class=EffectClass[sigil_d["effect_class"]],
            resonance_ceiling=float(sigil_d["resonance_ceiling"]),
            contradiction_severity=ContradictionSeverity[sigil_d["contradiction_severity"]],
            semantic_fingerprint=str(sigil_d.get("semantic_fingerprint") or ""),
            semantic_vector=SemanticVector(
                components=tuple(float(x) for x in sigil_d["semantic_vector"]),
                basis_version=basis_version,
            ),
            polarity=Polarity[str(sigil_d["polarity"])],
        )
        return CrystallizedSigil.model_construct(
            name=row["name"],
            sigil=sigil,
            source_seed_id=row["source_seed_id"],
            crystallized_at=datetime.fromisoformat(row["crystallized_at"]),
            generation=int(row["generation"]),
        )

    def write_crystallized_sigil(self, crystal: CrystallizedSigil) -> None:
        try:
            d = self._serialize_crystallized_sigil(crystal)
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO crystallized_sigils (
                    name, sigil_json, source_seed_id, crystallized_at,
                    generation, aspect_pattern_json, basis_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d["name"],
                    d["sigil_json"],
                    d["source_seed_id"],
                    d["crystallized_at"],
                    d["generation"],
                    d["aspect_pattern_json"],
                    d["basis_version"],
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_crystallized_sigil(self, name: str) -> CrystallizedSigil:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM crystallized_sigils WHERE name = ?", (name,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(name)
            return self._deserialize_crystallized_sigil(row)
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def crystallized_for_aspects(
        self, aspects: frozenset[Aspect]
    ) -> CrystallizedSigil | None:
        try:
            pattern_json = json.dumps([a.name for a in aspects])
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT * FROM crystallized_sigils
                WHERE aspect_pattern_json = ?
                ORDER BY generation DESC
                LIMIT 1
                """,
                (pattern_json,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._deserialize_crystallized_sigil(row)
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_crystallized_sigils(self) -> list[CrystallizedSigil]:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM crystallized_sigils ORDER BY crystallized_at DESC")
            return [self._deserialize_crystallized_sigil(row) for row in cur.fetchall()]
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
