from __future__ import annotations

import json
import sqlite3
from typing import Optional

from vermyth.registry import AspectRegistry
from vermyth.schema import Aspect, EffectClass, GlyphSeed, SemanticVector


class SeedRepository:
    """Repository methods for glyph seed persistence."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def _serialize_glyph_seed(self, seed: GlyphSeed) -> dict:
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
            "generation": int(seed.generation),
            "semantic_vector_json": json.dumps(list(seed.semantic_vector.components)),
            "basis_version": seed.semantic_vector.normalized_basis_version(),
        }

    def _deserialize_glyph_seed(self, row: sqlite3.Row) -> GlyphSeed:
        names = json.loads(row["aspect_pattern_json"])
        pattern = frozenset(AspectRegistry.get().resolve(n) for n in names)
        comps = json.loads(row["semantic_vector_json"])
        dim = AspectRegistry.get().dimensionality
        sv_comps = [float(x) for x in comps]
        if len(sv_comps) < dim:
            sv_comps.extend(0.0 for _ in range(dim - len(sv_comps)))
        seed_basis = (
            int(row["basis_version"])
            if "basis_version" in row.keys() and row["basis_version"] is not None
            else 0
        )
        sv = SemanticVector(components=tuple(sv_comps), basis_version=seed_basis)
        cand_raw = row["candidate_effect_class"]
        cand: EffectClass | None = EffectClass[cand_raw] if cand_raw is not None else None
        return GlyphSeed.model_construct(
            seed_id=row["seed_id"],
            aspect_pattern=pattern,
            observed_count=int(row["observed_count"]),
            mean_resonance=float(row["mean_resonance"]),
            coherence_rate=float(row["coherence_rate"]),
            candidate_effect_class=cand,
            crystallized=bool(row["crystallized"]),
            generation=int(row["generation"]) if "generation" in row.keys() else 1,
            semantic_vector=sv,
        )

    def write_seed(self, seed: GlyphSeed) -> None:
        try:
            d = self._serialize_glyph_seed(seed)
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO glyph_seeds (
                    seed_id, aspect_pattern_json, observed_count, mean_resonance,
                    coherence_rate, candidate_effect_class, crystallized,
                    generation, semantic_vector_json, basis_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d["seed_id"],
                    d["aspect_pattern_json"],
                    d["observed_count"],
                    d["mean_resonance"],
                    d["coherence_rate"],
                    d["candidate_effect_class"],
                    d["crystallized"],
                    d["generation"],
                    d["semantic_vector_json"],
                    d["basis_version"],
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
        aspect_pattern: Optional[frozenset[Aspect]],
        crystallized: Optional[bool],
    ) -> list[GlyphSeed]:
        try:
            cur = self._conn.cursor()
            where: list[str] = []
            params: list[object] = []
            if aspect_pattern is not None:
                where.append("aspect_pattern_json = ?")
                params.append(json.dumps([a.name for a in aspect_pattern]))
            if crystallized is not None:
                where.append("crystallized = ?")
                params.append(1 if crystallized else 0)
            where_sql = ""
            if where:
                where_sql = " WHERE " + " AND ".join(where)
            cur.execute(f"SELECT * FROM glyph_seeds{where_sql}", tuple(params))
            return [self._deserialize_glyph_seed(r) for r in cur.fetchall()]
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
