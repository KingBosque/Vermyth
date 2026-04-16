from __future__ import annotations

import heapq
import json
import sqlite3
from datetime import datetime
from typing import Any

from vermyth.engine.keys import canonical_aspect_key
from vermyth.registry import AspectRegistry
from vermyth.schema import (
    CastProvenance,
    CastResult,
    ContradictionSeverity,
    EffectClass,
    Intent,
    IntentVector,
    Lineage,
    Polarity,
    ProjectionMethod,
    ResonanceScore,
    SemanticQuery,
    SemanticVector,
    Sigil,
    Verdict,
    VerdictType,
)


class CastRepository:
    """Repository methods for cast result persistence."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def _serialize_cast_result(self, result: CastResult) -> dict[str, Any]:
        sigil_json = json.dumps(
            {
                "name": result.sigil.name,
                "aspects": [a.name for a in result.sigil.aspects],
                "effect_class": result.sigil.effect_class.name,
                "resonance_ceiling": result.sigil.resonance_ceiling,
                "contradiction_severity": result.sigil.contradiction_severity.name,
                "semantic_fingerprint": result.sigil.semantic_fingerprint,
                "semantic_vector": list(result.sigil.semantic_vector.components),
                "basis_version": result.sigil.semantic_vector.normalized_basis_version(),
                "polarity": result.sigil.polarity.name,
            }
        )
        iv = result.verdict.intent_vector
        verdict_json = json.dumps(
            {
                "verdict_type": result.verdict.verdict_type.name,
                "resonance": {
                    "raw": result.verdict.resonance.raw,
                    "adjusted": result.verdict.resonance.adjusted,
                    "ceiling_applied": result.verdict.resonance.ceiling_applied,
                    "proof": result.verdict.resonance.proof,
                },
                "effect_description": result.verdict.effect_description,
                "incoherence_reason": result.verdict.incoherence_reason,
                "casting_note": result.verdict.casting_note,
                "intent_vector": {
                    "vector": {
                        "components": list(iv.vector.components),
                        "basis_version": iv.vector.normalized_basis_version(),
                    },
                    "projection_method": iv.projection_method.name,
                    "constraint_component": {
                        "components": list(iv.constraint_component.components),
                        "basis_version": iv.constraint_component.normalized_basis_version(),
                    },
                    "semantic_component": (
                        {
                            "components": list(iv.semantic_component.components),
                            "basis_version": iv.semantic_component.normalized_basis_version(),
                        }
                        if iv.semantic_component
                        else None
                    ),
                    "confidence": iv.confidence,
                },
            }
        )
        return {
            "cast_id": result.cast_id,
            "timestamp": result.timestamp.isoformat(),
            "intent_json": result.intent.model_dump_json(),
            "sigil_json": sigil_json,
            "verdict_json": verdict_json,
            "lineage_json": (
                result.lineage.model_dump_json()
                if result.lineage is not None
                else None
            ),
            "glyph_seed_id": result.glyph_seed_id,
            "provenance_json": (
                result.provenance.model_dump_json()
                if result.provenance is not None
                else None
            ),
            "narrative_coherence": (
                float(result.provenance.narrative_coherence)
                if result.provenance is not None
                and result.provenance.narrative_coherence is not None
                else None
            ),
            "causal_root_cast_id": (
                result.provenance.causal_root_cast_id
                if result.provenance is not None
                else None
            ),
            "semantic_vector_json": json.dumps(list(result.sigil.semantic_vector.components)),
            "basis_version": result.sigil.semantic_vector.normalized_basis_version(),
            "verdict_type": result.verdict.verdict_type.name,
            "effect_class": result.sigil.effect_class.name,
            "adjusted_resonance": result.verdict.resonance.adjusted,
            "branch_id": result.lineage.branch_id if result.lineage is not None else None,
            "aspect_pattern_key": canonical_aspect_key(result.sigil.aspects),
        }

    def _deserialize_cast_result(self, row: sqlite3.Row) -> CastResult:
        intent = Intent.model_validate_json(row["intent_json"])
        sigil_d = json.loads(row["sigil_json"])
        aspects = frozenset(AspectRegistry.get().resolve(n) for n in sigil_d["aspects"])
        cast_basis = (
            int(row["basis_version"])
            if "basis_version" in row.keys() and row["basis_version"] is not None
            else 0
        )
        sigil_components = sigil_d.get("semantic_vector")
        if not isinstance(sigil_components, list):
            sigil_components = json.loads(row["semantic_vector_json"])
        sigil = Sigil.model_construct(
            name=sigil_d["name"],
            aspects=aspects,
            effect_class=EffectClass[sigil_d["effect_class"]],
            resonance_ceiling=float(sigil_d["resonance_ceiling"]),
            contradiction_severity=ContradictionSeverity[sigil_d["contradiction_severity"]],
            semantic_fingerprint=str(sigil_d.get("semantic_fingerprint") or ""),
            semantic_vector=SemanticVector(
                components=tuple(float(x) for x in sigil_components),
                basis_version=cast_basis,
            ),
            polarity=Polarity[str(sigil_d["polarity"])],
        )
        vj = json.loads(row["verdict_json"])
        res = vj["resonance"]
        resonance = ResonanceScore(
            raw=res["raw"],
            adjusted=res["adjusted"],
            ceiling_applied=res["ceiling_applied"],
            proof=res["proof"],
        )
        iv_raw = vj["intent_vector"]
        dim = AspectRegistry.get().dimensionality
        iv_vec_raw = iv_raw["vector"]
        iv_cc_raw = iv_raw["constraint_component"]
        vec_basis = cast_basis
        cc_basis = cast_basis
        vec_source = iv_vec_raw
        cc_source = iv_cc_raw
        if isinstance(iv_vec_raw, dict):
            vec_source = iv_vec_raw.get("components", [])
            vec_basis = int(iv_vec_raw.get("basis_version", cast_basis))
        if isinstance(iv_cc_raw, dict):
            cc_source = iv_cc_raw.get("components", [])
            cc_basis = int(iv_cc_raw.get("basis_version", cast_basis))
        vec_comps = [float(x) for x in vec_source]
        if len(vec_comps) < dim:
            vec_comps.extend(0.0 for _ in range(dim - len(vec_comps)))
        cc_comps = [float(x) for x in cc_source]
        if len(cc_comps) < dim:
            cc_comps.extend(0.0 for _ in range(dim - len(cc_comps)))
        vec = SemanticVector(components=tuple(vec_comps), basis_version=vec_basis)
        cc = SemanticVector(components=tuple(cc_comps), basis_version=cc_basis)
        sc: SemanticVector | None = None
        if iv_raw["semantic_component"] is not None:
            sc_raw = iv_raw["semantic_component"]
            sc_source = sc_raw
            sc_basis = cast_basis
            if isinstance(sc_raw, dict):
                sc_source = sc_raw.get("components", [])
                sc_basis = int(sc_raw.get("basis_version", cast_basis))
            sc_comps = [float(x) for x in sc_source]
            if len(sc_comps) < dim:
                sc_comps.extend(0.0 for _ in range(dim - len(sc_comps)))
            sc = SemanticVector(components=tuple(sc_comps), basis_version=sc_basis)
        intent_vector = IntentVector(
            vector=vec,
            projection_method=ProjectionMethod[iv_raw["projection_method"]],
            constraint_component=cc,
            semantic_component=sc,
            confidence=iv_raw["confidence"],
        )
        verdict = Verdict(
            verdict_type=VerdictType[vj["verdict_type"]],
            resonance=resonance,
            effect_description=vj["effect_description"],
            incoherence_reason=vj["incoherence_reason"],
            casting_note=vj["casting_note"],
            intent_vector=intent_vector,
        )
        lineage: Lineage | None = None
        lj = row["lineage_json"]
        if lj is not None:
            lineage = Lineage.model_validate_json(lj)
        provenance: CastProvenance | None = None
        pj = row.get("provenance_json") if hasattr(row, "get") else None
        if pj is None:
            try:
                pj = row["provenance_json"]
            except Exception:
                pj = None
        if pj is not None:
            provenance = CastProvenance.model_validate_json(pj)
        elif (
            "narrative_coherence" in row.keys()
            and row["narrative_coherence"] is not None
        ) or (
            "causal_root_cast_id" in row.keys()
            and row["causal_root_cast_id"] is not None
        ):
            provenance = CastProvenance(
                source="base",
                narrative_coherence=(
                    float(row["narrative_coherence"])
                    if row["narrative_coherence"] is not None
                    else None
                ),
                causal_root_cast_id=(
                    str(row["causal_root_cast_id"])
                    if row["causal_root_cast_id"] is not None
                    else None
                ),
            )
        ts = datetime.fromisoformat(row["timestamp"])
        return CastResult.model_construct(
            cast_id=row["cast_id"],
            timestamp=ts,
            intent=intent,
            sigil=sigil,
            verdict=verdict,
            immutable=True,
            lineage=lineage,
            glyph_seed_id=row["glyph_seed_id"],
            provenance=provenance,
        )

    def write(self, result: CastResult) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT 1 FROM cast_results WHERE cast_id = ?", (result.cast_id,))
            if cur.fetchone() is not None:
                raise ValueError(f"CastResult with cast_id {result.cast_id!r} already exists")
            d = self._serialize_cast_result(result)
            cur.execute(
                """
                INSERT INTO cast_results (
                    cast_id, timestamp, intent_json, sigil_json, verdict_json,
                    lineage_json, glyph_seed_id, semantic_vector_json,
                    verdict_type, effect_class, adjusted_resonance, branch_id,
                    provenance_json, aspect_pattern_key, basis_version,
                    narrative_coherence, causal_root_cast_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d["cast_id"],
                    d["timestamp"],
                    d["intent_json"],
                    d["sigil_json"],
                    d["verdict_json"],
                    d["lineage_json"],
                    d["glyph_seed_id"],
                    d["semantic_vector_json"],
                    d["verdict_type"],
                    d["effect_class"],
                    d["adjusted_resonance"],
                    d["branch_id"],
                    d["provenance_json"],
                    d["aspect_pattern_key"],
                    d["basis_version"],
                    d["narrative_coherence"],
                    d["causal_root_cast_id"],
                ),
            )
            self._conn.commit()
        except ValueError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read(self, cast_id: str) -> CastResult:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM cast_results WHERE cast_id = ?", (cast_id,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(cast_id)
            return self._deserialize_cast_result(row)
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query(self, query: SemanticQuery) -> list[CastResult]:
        try:
            parts: list[str] = []
            params: list[Any] = []
            if query.verdict_filter is not None:
                parts.append("verdict_type = ?")
                params.append(query.verdict_filter.name)
            if query.effect_class_filter is not None:
                parts.append("effect_class = ?")
                params.append(query.effect_class_filter.name)
            if query.min_resonance is not None:
                parts.append("adjusted_resonance >= ?")
                params.append(query.min_resonance)
            if query.branch_id is not None:
                parts.append("branch_id = ?")
                params.append(query.branch_id)
            if query.aspect_filter is not None:
                parts.append("aspect_pattern_key = ?")
                params.append(canonical_aspect_key(query.aspect_filter))
            where = (" WHERE " + " AND ".join(parts)) if parts else ""
            sql = "SELECT * FROM cast_results" + where + " ORDER BY timestamp DESC" + " LIMIT ?"
            cur = self._conn.cursor()
            cur.execute(sql, tuple(params) + (int(query.limit),))
            return [self._deserialize_cast_result(row) for row in cur.fetchall()]
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def semantic_search(self, query: SemanticQuery) -> list[CastResult]:
        if query.proximity_to is None or query.proximity_threshold is None:
            raise ValueError("proximity_to and proximity_threshold are required")
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT cast_id, semantic_vector_json, basis_version FROM cast_results")
            top: list[tuple[float, str]] = []
            limit = int(query.limit)
            thr = float(query.proximity_threshold)
            for row in cur.fetchall():
                comps = json.loads(row["semantic_vector_json"])
                basis_version = (
                    int(row["basis_version"])
                    if "basis_version" in row.keys() and row["basis_version"] is not None
                    else 0
                )
                sv = SemanticVector(
                    components=tuple(float(x) for x in comps),
                    basis_version=basis_version,
                )
                sim = query.proximity_to.cosine_similarity(sv)
                if sim < thr:
                    continue
                item = (sim, row["cast_id"])
                if len(top) < limit:
                    heapq.heappush(top, item)
                    continue
                if limit > 0 and item[0] > top[0][0]:
                    heapq.heapreplace(top, item)

            top.sort(key=lambda t: -t[0])
            ids = [cid for _, cid in top]
            if not ids:
                return []
            placeholders = ",".join("?" for _ in ids)
            cur.execute(
                f"SELECT * FROM cast_results WHERE cast_id IN ({placeholders})",
                tuple(ids),
            )
            by_id: dict[str, CastResult] = {}
            for row in cur.fetchall():
                cr = self._deserialize_cast_result(row)
                by_id[cr.cast_id] = cr
            return [by_id[cid] for cid in ids if cid in by_id]
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def delete(self, cast_id: str) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM cast_results WHERE cast_id = ?", (cast_id,))
            if cur.rowcount == 0:
                raise KeyError(cast_id)
            self._conn.commit()
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
