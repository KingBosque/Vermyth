"""SQLite-backed grimoire: CastResult and GlyphSeed persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from vermyth.contracts import GrimoireContract
from vermyth.schema import (
    AspectID,
    CastResult,
    ContradictionSeverity,
    EffectClass,
    GlyphSeed,
    Intent,
    IntentVector,
    Lineage,
    ProjectionMethod,
    ResonanceScore,
    SemanticQuery,
    SemanticVector,
    Sigil,
    Verdict,
    VerdictType,
)


class Grimoire(GrimoireContract):
    """Persistent cast and seed storage using SQLite."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self._path = Path.home() / ".vermyth" / "grimoire.db"
        else:
            self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._run_migrations()

    def _run_migrations(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        has_migrations = cur.fetchone() is not None
        if has_migrations:
            cur.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?", ("v001",)
            )
            if cur.fetchone() is not None:
                return
        sql_path = Path(__file__).parent / "migrations" / "v001_initial.sql"
        self._conn.executescript(sql_path.read_text(encoding="utf-8"))
        cur.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            ("v001", datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

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
                    "vector": list(iv.vector.components),
                    "projection_method": iv.projection_method.name,
                    "constraint_component": list(iv.constraint_component.components),
                    "semantic_component": (
                        list(iv.semantic_component.components)
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
            "semantic_vector_json": json.dumps(
                list(result.sigil.semantic_vector.components)
            ),
            "verdict_type": result.verdict.verdict_type.name,
            "effect_class": result.sigil.effect_class.name,
            "adjusted_resonance": result.verdict.resonance.adjusted,
            "branch_id": (
                result.lineage.branch_id if result.lineage is not None else None
            ),
        }

    def _deserialize_cast_result(self, row: sqlite3.Row) -> CastResult:
        """Reconstruct CastResult from a DB row.

        Uses ``CastResult.model_construct`` so ``cast_id`` and ``timestamp`` can
        be restored from storage; the normal constructor rejects caller-supplied
        values for those fields.
        """
        intent = Intent.model_validate_json(row["intent_json"])
        sigil_d = json.loads(row["sigil_json"])
        aspects = frozenset(AspectID[n] for n in sigil_d["aspects"])
        sigil = Sigil.model_validate(
            {
                "name": sigil_d["name"],
                "aspects": aspects,
                "effect_class": EffectClass[sigil_d["effect_class"]],
                "resonance_ceiling": sigil_d["resonance_ceiling"],
                "contradiction_severity": ContradictionSeverity[
                    sigil_d["contradiction_severity"]
                ],
            }
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
        vec = SemanticVector(
            components=tuple(float(x) for x in iv_raw["vector"])
        )
        cc = SemanticVector(
            components=tuple(float(x) for x in iv_raw["constraint_component"])
        )
        sc: SemanticVector | None = None
        if iv_raw["semantic_component"] is not None:
            sc = SemanticVector(
                components=tuple(float(x) for x in iv_raw["semantic_component"])
            )
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
        )

    def _serialize_glyph_seed(self, seed: GlyphSeed) -> dict[str, Any]:
        cand = (
            seed.candidate_effect_class.name
            if seed.candidate_effect_class is not None
            else None
        )
        return {
            "seed_id": seed.seed_id,
            "aspect_pattern_json": json.dumps([a.name for a in seed.aspect_pattern]),
            "observed_count": seed.observed_count,
            "mean_resonance": seed.mean_resonance,
            "coherence_rate": seed.coherence_rate,
            "candidate_effect_class": cand,
            "crystallized": 1 if seed.crystallized else 0,
            "semantic_vector_json": json.dumps(
                list(seed.semantic_vector.components)
            ),
        }

    def _deserialize_glyph_seed(self, row: sqlite3.Row) -> GlyphSeed:
        """Reconstruct GlyphSeed from a DB row.

        Uses ``GlyphSeed.model_construct`` with an explicit ``seed_id`` so stored
        seeds round-trip; the normal constructor forbids supplying ``seed_id``.
        """
        names = json.loads(row["aspect_pattern_json"])
        pattern = frozenset(AspectID[n] for n in names)
        comps = json.loads(row["semantic_vector_json"])
        sv = SemanticVector(components=tuple(float(x) for x in comps))
        cand_raw = row["candidate_effect_class"]
        cand: EffectClass | None = (
            EffectClass[cand_raw] if cand_raw is not None else None
        )
        return GlyphSeed.model_construct(
            seed_id=row["seed_id"],
            aspect_pattern=pattern,
            observed_count=int(row["observed_count"]),
            mean_resonance=float(row["mean_resonance"]),
            coherence_rate=float(row["coherence_rate"]),
            candidate_effect_class=cand,
            crystallized=bool(row["crystallized"]),
            semantic_vector=sv,
        )

    def write(self, result: CastResult) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT 1 FROM cast_results WHERE cast_id = ?",
                (result.cast_id,),
            )
            if cur.fetchone() is not None:
                raise ValueError(
                    f"CastResult with cast_id {result.cast_id!r} already exists"
                )
            d = self._serialize_cast_result(result)
            cur.execute(
                """
                INSERT INTO cast_results (
                    cast_id, timestamp, intent_json, sigil_json, verdict_json,
                    lineage_json, glyph_seed_id, semantic_vector_json,
                    verdict_type, effect_class, adjusted_resonance, branch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            where = (" WHERE " + " AND ".join(parts)) if parts else ""
            sql = (
                "SELECT * FROM cast_results"
                + where
                + " ORDER BY timestamp DESC"
            )
            cur = self._conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            out: list[CastResult] = []
            for row in rows:
                cr = self._deserialize_cast_result(row)
                if query.aspect_filter is not None:
                    if cr.sigil.aspects != query.aspect_filter:
                        continue
                out.append(cr)
                if len(out) >= query.limit:
                    break
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def semantic_search(self, query: SemanticQuery) -> list[CastResult]:
        if query.proximity_to is None or query.proximity_threshold is None:
            raise ValueError("proximity_to and proximity_threshold are required")
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT cast_id, semantic_vector_json FROM cast_results"
            )
            scored: list[tuple[float, str]] = []
            for row in cur.fetchall():
                comps = json.loads(row["semantic_vector_json"])
                sv = SemanticVector(
                    components=tuple(float(x) for x in comps)
                )
                sim = query.proximity_to.cosine_similarity(sv)
                if sim >= query.proximity_threshold:
                    scored.append((sim, row["cast_id"]))
            scored.sort(key=lambda t: -t[0])
            ids = [cid for _, cid in scored[: query.limit]]
            return [self.read(cid) for cid in ids]
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def write_seed(self, seed: GlyphSeed) -> None:
        try:
            d = self._serialize_glyph_seed(seed)
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO glyph_seeds (
                    seed_id, aspect_pattern_json, observed_count, mean_resonance,
                    coherence_rate, candidate_effect_class, crystallized,
                    semantic_vector_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d["seed_id"],
                    d["aspect_pattern_json"],
                    d["observed_count"],
                    d["mean_resonance"],
                    d["coherence_rate"],
                    d["candidate_effect_class"],
                    d["crystallized"],
                    d["semantic_vector_json"],
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_seed(self, seed_id: str) -> GlyphSeed:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM glyph_seeds WHERE seed_id = ?", (seed_id,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(seed_id)
            return self._deserialize_glyph_seed(row)
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_seeds(
        self,
        aspect_pattern: Optional[frozenset[AspectID]],
        crystallized: Optional[bool],
    ) -> list[GlyphSeed]:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM glyph_seeds")
            seeds = [self._deserialize_glyph_seed(r) for r in cur.fetchall()]
            out: list[GlyphSeed] = []
            for s in seeds:
                if aspect_pattern is not None and s.aspect_pattern != aspect_pattern:
                    continue
                if crystallized is not None and s.crystallized != crystallized:
                    continue
                out.append(s)
            return out
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

    def close(self) -> None:
        """Close the underlying SQLite connection. Call when the Grimoire is no longer needed."""
        self._conn.close()
