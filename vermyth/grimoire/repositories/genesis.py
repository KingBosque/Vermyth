from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from vermyth.registry import AspectRegistry
from vermyth.schema import EmergentAspect, GenesisStatus, RegisteredAspect, SemanticVector

from vermyth.grimoire.repositories.registry import RegistryRepository


def _centroid_payload(raw_json: str, basis_version: int) -> dict[str, Any]:
    loaded = json.loads(raw_json)
    if isinstance(loaded, dict):
        comps = loaded.get("components", [])
        payload = {"components": comps, "basis_version": int(basis_version)}
        if loaded.get("basis_version") is not None:
            payload["basis_version"] = int(loaded["basis_version"])
        return payload
    return {"components": loaded, "basis_version": int(basis_version)}


class GenesisRepository:
    def __init__(self, conn: sqlite3.Connection, registry: RegistryRepository) -> None:
        self._conn = conn
        self._registry = registry

    def write_emergent_aspect(self, aspect: EmergentAspect) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO emergent_aspects (
                    genesis_id, proposed_name, derived_polarity, derived_entropy,
                    proposed_symbol, centroid_vector_json, support_count,
                    mean_resonance, coherence_rate, status, proposed_at, decided_at,
                    reviewed_by, reviewed_at, review_note, evidence_cast_ids_json, basis_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(genesis_id) DO UPDATE SET
                    proposed_name=excluded.proposed_name,
                    derived_polarity=excluded.derived_polarity,
                    derived_entropy=excluded.derived_entropy,
                    proposed_symbol=excluded.proposed_symbol,
                    centroid_vector_json=excluded.centroid_vector_json,
                    support_count=excluded.support_count,
                    mean_resonance=excluded.mean_resonance,
                    coherence_rate=excluded.coherence_rate,
                    status=excluded.status,
                    proposed_at=excluded.proposed_at,
                    decided_at=excluded.decided_at,
                    reviewed_by=excluded.reviewed_by,
                    reviewed_at=excluded.reviewed_at,
                    review_note=excluded.review_note,
                    evidence_cast_ids_json=excluded.evidence_cast_ids_json,
                    basis_version=excluded.basis_version
                """,
                (
                    aspect.genesis_id,
                    aspect.proposed_name,
                    int(aspect.derived_polarity),
                    float(aspect.derived_entropy),
                    aspect.proposed_symbol,
                    json.dumps(aspect.centroid_vector.model_dump()),
                    int(aspect.support_count),
                    float(aspect.mean_resonance),
                    float(aspect.coherence_rate),
                    aspect.status.value,
                    aspect.proposed_at.isoformat(),
                    aspect.decided_at.isoformat() if aspect.decided_at else None,
                    aspect.reviewed_by,
                    aspect.reviewed_at.isoformat() if aspect.reviewed_at else None,
                    aspect.review_note,
                    json.dumps(list(aspect.evidence_cast_ids)),
                    aspect.centroid_vector.normalized_basis_version(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM emergent_aspects WHERE genesis_id = ?",
                (str(genesis_id),),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(genesis_id))
            decided_at = row["decided_at"]
            reviewed_at = row["reviewed_at"] if "reviewed_at" in row.keys() else None
            basis_version = (
                int(row["basis_version"])
                if "basis_version" in row.keys() and row["basis_version"] is not None
                else 0
            )
            return EmergentAspect(
                genesis_id=str(row["genesis_id"]),
                proposed_name=str(row["proposed_name"]),
                derived_polarity=int(row["derived_polarity"]),
                derived_entropy=float(row["derived_entropy"]),
                proposed_symbol=str(row["proposed_symbol"]),
                centroid_vector=SemanticVector.model_validate(
                    _centroid_payload(row["centroid_vector_json"], basis_version)
                ),
                support_count=int(row["support_count"]),
                mean_resonance=float(row["mean_resonance"]),
                coherence_rate=float(row["coherence_rate"]),
                status=GenesisStatus(str(row["status"])),
                proposed_at=datetime.fromisoformat(str(row["proposed_at"])),
                decided_at=datetime.fromisoformat(str(decided_at)) if decided_at else None,
                reviewed_by=(str(row["reviewed_by"]) if row["reviewed_by"] else None),
                reviewed_at=(datetime.fromisoformat(str(reviewed_at)) if reviewed_at else None),
                review_note=(str(row["review_note"]) if row["review_note"] else None),
                evidence_cast_ids=json.loads(row["evidence_cast_ids_json"]),
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_emergent_aspects(
        self, status: str | None = None, limit: int = 50
    ) -> list[EmergentAspect]:
        try:
            cur = self._conn.cursor()
            if status is None:
                cur.execute(
                    """
                    SELECT * FROM emergent_aspects
                    ORDER BY proposed_at DESC
                    LIMIT ?
                    """,
                    (int(limit),),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM emergent_aspects
                    WHERE status = ?
                    ORDER BY proposed_at DESC
                    LIMIT ?
                    """,
                    (str(status), int(limit)),
                )
            out: list[EmergentAspect] = []
            for row in cur.fetchall():
                decided_at = row["decided_at"]
                reviewed_at = row["reviewed_at"] if "reviewed_at" in row.keys() else None
                basis_version = (
                    int(row["basis_version"])
                    if "basis_version" in row.keys() and row["basis_version"] is not None
                    else 0
                )
                out.append(
                    EmergentAspect(
                        genesis_id=str(row["genesis_id"]),
                        proposed_name=str(row["proposed_name"]),
                        derived_polarity=int(row["derived_polarity"]),
                        derived_entropy=float(row["derived_entropy"]),
                        proposed_symbol=str(row["proposed_symbol"]),
                        centroid_vector=SemanticVector.model_validate(
                            _centroid_payload(row["centroid_vector_json"], basis_version)
                        ),
                        support_count=int(row["support_count"]),
                        mean_resonance=float(row["mean_resonance"]),
                        coherence_rate=float(row["coherence_rate"]),
                        status=GenesisStatus(str(row["status"])),
                        proposed_at=datetime.fromisoformat(str(row["proposed_at"])),
                        decided_at=(
                            datetime.fromisoformat(str(decided_at)) if decided_at else None
                        ),
                        reviewed_by=(
                            str(row["reviewed_by"]) if row["reviewed_by"] else None
                        ),
                        reviewed_at=(
                            datetime.fromisoformat(str(reviewed_at)) if reviewed_at else None
                        ),
                        review_note=(
                            str(row["review_note"]) if row["review_note"] else None
                        ),
                        evidence_cast_ids=json.loads(row["evidence_cast_ids_json"]),
                    )
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def accept_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        aspect = self.read_emergent_aspect(genesis_id)
        if aspect.reviewed_at is None:
            raise RuntimeError("genesis proposal must be reviewed before acceptance")
        accepted = EmergentAspect.model_construct(
            genesis_id=aspect.genesis_id,
            proposed_name=aspect.proposed_name,
            derived_polarity=aspect.derived_polarity,
            derived_entropy=aspect.derived_entropy,
            proposed_symbol=aspect.proposed_symbol,
            centroid_vector=aspect.centroid_vector,
            support_count=aspect.support_count,
            mean_resonance=aspect.mean_resonance,
            coherence_rate=aspect.coherence_rate,
            status=GenesisStatus.ACCEPTED,
            proposed_at=aspect.proposed_at,
            decided_at=datetime.now(timezone.utc),
            reviewed_by=aspect.reviewed_by,
            reviewed_at=aspect.reviewed_at,
            review_note=aspect.review_note,
            evidence_cast_ids=aspect.evidence_cast_ids,
        )
        registry = AspectRegistry.get()
        reg = RegisteredAspect(
            name=accepted.proposed_name,
            polarity=int(accepted.derived_polarity),
            entropy_coefficient=float(accepted.derived_entropy),
            symbol=accepted.proposed_symbol,
        )
        if not registry.is_registered(reg.name):
            registry.register(reg)
            self._registry.write_registered_aspect(reg, registry.dimensionality - 1)
        self.write_emergent_aspect(accepted)
        return accepted

    def reject_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        aspect = self.read_emergent_aspect(genesis_id)
        rejected = EmergentAspect.model_construct(
            genesis_id=aspect.genesis_id,
            proposed_name=aspect.proposed_name,
            derived_polarity=aspect.derived_polarity,
            derived_entropy=aspect.derived_entropy,
            proposed_symbol=aspect.proposed_symbol,
            centroid_vector=aspect.centroid_vector,
            support_count=aspect.support_count,
            mean_resonance=aspect.mean_resonance,
            coherence_rate=aspect.coherence_rate,
            status=GenesisStatus.REJECTED,
            proposed_at=aspect.proposed_at,
            decided_at=datetime.now(timezone.utc),
            reviewed_by=aspect.reviewed_by,
            reviewed_at=aspect.reviewed_at,
            review_note=aspect.review_note,
            evidence_cast_ids=aspect.evidence_cast_ids,
        )
        self.write_emergent_aspect(rejected)
        return rejected

    def review_emergent_aspect(self, genesis_id: str, reviewer: str, note: str | None) -> EmergentAspect:
        aspect = self.read_emergent_aspect(genesis_id)
        reviewed = EmergentAspect.model_construct(
            genesis_id=aspect.genesis_id,
            proposed_name=aspect.proposed_name,
            derived_polarity=aspect.derived_polarity,
            derived_entropy=aspect.derived_entropy,
            proposed_symbol=aspect.proposed_symbol,
            centroid_vector=aspect.centroid_vector,
            support_count=aspect.support_count,
            mean_resonance=aspect.mean_resonance,
            coherence_rate=aspect.coherence_rate,
            status=aspect.status,
            proposed_at=aspect.proposed_at,
            decided_at=aspect.decided_at,
            reviewed_by=str(reviewer),
            reviewed_at=datetime.now(timezone.utc),
            review_note=note,
            evidence_cast_ids=aspect.evidence_cast_ids,
        )
        self.write_emergent_aspect(reviewed)
        return reviewed
"""Emergent genesis repository split placeholder."""

