"""MCP tool handlers: Vermyth engine and grimoire wiring (no JSON-RPC protocol)."""

from __future__ import annotations

from typing import Any, Optional

from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.schema import (
    AspectID,
    CastResult,
    GlyphSeed,
    Intent,
    SemanticQuery,
    SemanticVector,
    VerdictType,
)


class VermythTools:
    """Execute MCP tools against a ResonanceEngine and Grimoire."""

    def __init__(self, engine: ResonanceEngine, grimoire: Grimoire) -> None:
        self._engine = engine
        self._grimoire = grimoire

    def _cast_result_to_dict(self, result: CastResult) -> dict[str, Any]:
        lineage_dict: dict[str, Any] | None = None
        if result.lineage is not None:
            lineage_dict = {
                "parent_cast_id": result.lineage.parent_cast_id,
                "depth": result.lineage.depth,
                "branch_id": result.lineage.branch_id,
            }
        return {
            "cast_id": result.cast_id,
            "timestamp": result.timestamp.isoformat(),
            "verdict": result.verdict.verdict_type.name,
            "resonance": round(result.verdict.resonance.adjusted, 4),
            "effect_class": result.sigil.effect_class.name,
            "sigil_name": result.sigil.name,
            "sigil_aspects": sorted([a.name for a in result.sigil.aspects]),
            "effect_description": result.verdict.effect_description,
            "casting_note": result.verdict.casting_note,
            "incoherence_reason": result.verdict.incoherence_reason,
            "proof": result.verdict.resonance.proof,
            "projection_method": result.verdict.intent_vector.projection_method.name,
            "intent_confidence": round(result.verdict.intent_vector.confidence, 4),
            "semantic_vector": [
                round(c, 6) for c in result.sigil.semantic_vector.components
            ],
            "intent_vector": [
                round(c, 6) for c in result.verdict.intent_vector.vector.components
            ],
            "lineage": lineage_dict,
            "glyph_seed_id": result.glyph_seed_id,
        }

    def _seed_to_dict(self, seed: GlyphSeed) -> dict[str, Any]:
        return {
            "seed_id": seed.seed_id,
            "aspects": sorted([a.name for a in seed.aspect_pattern]),
            "observed_count": seed.observed_count,
            "mean_resonance": round(seed.mean_resonance, 4),
            "coherence_rate": round(seed.coherence_rate, 4),
            "candidate_effect_class": (
                seed.candidate_effect_class.name
                if seed.candidate_effect_class
                else None
            ),
            "crystallized": seed.crystallized,
            "semantic_vector": [
                round(c, 6) for c in seed.semantic_vector.components
            ],
        }

    def tool_cast(self, aspects: list[str], intent: dict) -> dict[str, Any]:
        try:
            resolved: list[AspectID] = []
            for name in aspects:
                try:
                    resolved.append(AspectID[name])
                except KeyError as exc:
                    raise ValueError(f"Unknown aspect: {name}") from exc
            aspects_set = frozenset(resolved)
            intent_obj = Intent(**intent)
            result = self._engine.cast(aspects_set, intent_obj)
            seeds = self._grimoire.query_seeds(
                aspect_pattern=aspects_set, crystallized=None
            )
            seed = self._engine.accumulate(result, seeds)
            if seed is not None:
                prev = next(
                    (s for s in seeds if s.aspect_pattern == seed.aspect_pattern),
                    None,
                )
                if prev is not None:
                    seed = GlyphSeed.model_construct(
                        seed_id=prev.seed_id,
                        aspect_pattern=seed.aspect_pattern,
                        observed_count=seed.observed_count,
                        mean_resonance=seed.mean_resonance,
                        coherence_rate=seed.coherence_rate,
                        candidate_effect_class=seed.candidate_effect_class,
                        crystallized=seed.crystallized,
                        semantic_vector=seed.semantic_vector,
                    )
                self._grimoire.write_seed(seed)
            out = self._cast_result_to_dict(result)
            if seed is not None and seed.observed_count >= 10:
                sig = self._engine.crystallize(seed)
                if sig is not None:
                    out["crystallized_sigil"] = {
                        "name": sig.name,
                        "effect_class": sig.effect_class.name,
                        "resonance_ceiling": sig.resonance_ceiling,
                    }
                    updated = GlyphSeed.model_construct(
                        seed_id=seed.seed_id,
                        aspect_pattern=seed.aspect_pattern,
                        observed_count=seed.observed_count,
                        mean_resonance=seed.mean_resonance,
                        coherence_rate=seed.coherence_rate,
                        candidate_effect_class=seed.candidate_effect_class,
                        crystallized=True,
                        semantic_vector=seed.semantic_vector,
                    )
                    self._grimoire.write_seed(updated)
            self._grimoire.write(result)
            return out
        except ValueError:
            raise
        except Exception as e:
            if (
                type(e).__name__ == "ValidationError"
                and type(e).__module__.startswith("pydantic")
            ):
                raise
            raise RuntimeError(f"cast failed: {e}") from e

    def tool_query(self, filters: dict) -> list[dict[str, Any]]:
        try:
            kwargs: dict[str, Any] = {}
            vf = filters.get("verdict_filter")
            if vf is not None:
                kwargs["verdict_filter"] = VerdictType[vf]
            mr = filters.get("min_resonance")
            if mr is not None:
                kwargs["min_resonance"] = float(mr)
            bid = filters.get("branch_id")
            if bid is not None:
                kwargs["branch_id"] = str(bid)
            if "limit" in filters and filters["limit"] is not None:
                kwargs["limit"] = int(filters["limit"])
            else:
                kwargs["limit"] = 20
            query = SemanticQuery(**kwargs)
            rows = self._grimoire.query(query)
            return [self._cast_result_to_dict(r) for r in rows]
        except ValueError:
            raise
        except Exception as e:
            if (
                type(e).__name__ == "ValidationError"
                and type(e).__module__.startswith("pydantic")
            ):
                raise
            raise RuntimeError(f"query failed: {e}") from e

    def tool_semantic_search(
        self, proximity_vector: list[float], threshold: float, limit: int
    ) -> list[dict[str, Any]]:
        try:
            if len(proximity_vector) != 6:
                raise ValueError("proximity_vector must have exactly 6 elements")
            for x in proximity_vector:
                xf = float(x)
                if xf < -1.0 or xf > 1.0:
                    raise ValueError(
                        "proximity_vector components must be between -1.0 and 1.0"
                    )
            if threshold < 0.0 or threshold > 1.0:
                raise ValueError("threshold must be between 0.0 and 1.0")
            vector = SemanticVector(
                components=tuple(float(c) for c in proximity_vector)
            )
            query = SemanticQuery(
                proximity_to=vector,
                proximity_threshold=float(threshold),
                limit=int(limit),
            )
            rows = self._grimoire.semantic_search(query)
            return [self._cast_result_to_dict(r) for r in rows]
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"semantic_search failed: {e}") from e

    def tool_inspect(self, cast_id: str) -> dict[str, Any]:
        try:
            result = self._grimoire.read(cast_id)
            return self._cast_result_to_dict(result)
        except KeyError:
            raise
        except Exception as e:
            raise RuntimeError(f"inspect failed: {e}") from e

    def tool_seeds(self, crystallized: Optional[bool]) -> list[dict[str, Any]]:
        try:
            seeds = self._grimoire.query_seeds(
                aspect_pattern=None, crystallized=crystallized
            )
            return [self._seed_to_dict(s) for s in seeds]
        except Exception as e:
            raise RuntimeError(f"seeds failed: {e}") from e