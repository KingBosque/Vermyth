import json
import math
from pathlib import Path

from vermyth.contracts import CompositionContract
from vermyth.engine.keys import canonical_aspect_key
from vermyth.schema import (
    Aspect,
    AspectID,
    ContradictionSeverity,
    EffectClass,
    FluidSigil,
    Polarity,
    SemanticVector,
    Sigil,
)


class CompositionEngine(CompositionContract):
    """Core engine: composition of AspectID sets into resolved Sigils from JSON tables."""

    def __init__(
        self,
        data_dir: Path | None = None,
        *,
        contradictions: dict[str, dict] | None = None,
    ) -> None:
        self._data_dir = (
            data_dir
            if data_dir is not None
            else Path(__file__).resolve().parent.parent / "data" / "sigils"
        )
        self._table: dict[str, dict] = {}
        self._contradictions: dict[str, dict] = {}
        self._load_table()
        if contradictions is None:
            self._load_contradictions()
        else:
            self._contradictions = contradictions

    @property
    def contradictions(self) -> dict[str, dict]:
        return self._contradictions

    def _load_contradictions(self) -> None:
        path = self._data_dir / "contradictions.json"
        with path.open(encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict):
            raise ValueError("contradictions.json must contain a JSON object")
        self._contradictions = loaded

    def _ingest_sigil_file(self, path: Path) -> None:
        with path.open(encoding="utf-8") as f:
            entries = json.load(f)
        if not isinstance(entries, list):
            raise ValueError(f"expected JSON array in {path.name}")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"invalid entry in {path.name}")
            raw_names = entry.get("aspects")
            if not isinstance(raw_names, list):
                raise ValueError(f"entry missing aspects array in {path.name}")
            aspect_set: set[AspectID] = set()
            for name in raw_names:
                if not isinstance(name, str):
                    raise ValueError(f"invalid aspect name in {path.name}")
                try:
                    aspect_set.add(AspectID[name])
                except KeyError as exc:
                    raise ValueError(f"unknown AspectID name: {name!r}") from exc
            aspects_fs = frozenset(aspect_set)
            key = canonical_aspect_key(aspects_fs)
            if key in self._table:
                raise ValueError(f"duplicate canonical sigil key: {key!r}")
            self._table[key] = entry

    def _load_table(self) -> None:
        for path in sorted(self._data_dir.glob("*.json")):
            if path.name == "contradictions.json":
                continue
            self._ingest_sigil_file(path)
        extended = self._data_dir / "extended"
        if extended.is_dir():
            for path in sorted(extended.glob("*.json")):
                self._ingest_sigil_file(path)

    def _canonical_key(self, aspects: frozenset[Aspect]) -> str:
        return canonical_aspect_key(aspects)

    def _contradiction_severity_for_key(self, key: str, raw: dict) -> ContradictionSeverity:
        sev_override = raw.get("contradiction_severity")
        if (
            isinstance(sev_override, str)
            and sev_override in ContradictionSeverity.__members__
        ):
            return ContradictionSeverity[sev_override]
        contra = self._contradictions.get(key)
        if contra is None:
            return ContradictionSeverity.NONE
        sev = contra.get("severity", "NONE")
        return ContradictionSeverity[sev]

    def _normalize_unit(self, vec: SemanticVector) -> SemanticVector:
        s = 0.0
        for c in vec.components:
            s += float(c) * float(c)
        n = math.sqrt(s)
        if n == 0.0 or not math.isfinite(n):
            return SemanticVector(
                components=tuple(0.0 for _ in vec.components),
                basis_version=vec.basis_version,
            )
        return SemanticVector(
            components=tuple(float(c) / n for c in vec.components),
            basis_version=vec.basis_version,
        )

    def compose(self, aspects: frozenset[Aspect]) -> Sigil:
        n = len(aspects)
        if n < 1:
            raise ValueError("aspects must contain at least one AspectID")
        if n > 3:
            raise ValueError("aspects must contain at most three AspectIDs")
        key = self._canonical_key(aspects)
        if key not in self._table:
            raise ValueError(f"no defined resolution for aspect combination: {key!r}")
        raw = self._table[key]
        contradiction_severity = self._contradiction_severity_for_key(key, raw)
        name = raw["name"]
        effect_class = EffectClass[raw["effect_class"]]
        resonance_ceiling = float(raw["resonance_ceiling"])
        return Sigil(
            name=name,
            aspects=aspects,
            effect_class=effect_class,
            resonance_ceiling=resonance_ceiling,
            contradiction_severity=contradiction_severity,
        )

    def interpolate(self, vector: SemanticVector, k: int = 3) -> FluidSigil:
        if k < 1:
            raise ValueError("k must be >= 1")

        vec = self._normalize_unit(vector)
        scored: list[tuple[float, str, dict, frozenset[AspectID]]] = []
        for key, raw in self._table.items():
            raw_names = raw.get("aspects")
            if not isinstance(raw_names, list):
                continue
            aspects_set: set[AspectID] = set()
            ok = True
            for name in raw_names:
                if not isinstance(name, str) or name not in AspectID.__members__:
                    ok = False
                    break
                aspects_set.add(AspectID[name])
            if not ok or not aspects_set:
                continue
            aspects_fs = frozenset(aspects_set)
            anchor_vec = SemanticVector.from_aspects(aspects_fs)
            sim = anchor_vec.cosine_similarity(vec)
            scored.append((sim, key, raw, aspects_fs))

        if not scored:
            raise ValueError("no sigil anchors available for interpolation")

        scored.sort(key=lambda t: t[0], reverse=True)
        neighbors = scored[: min(k, len(scored))]

        # Softmax weights over similarities for stability.
        sims = [n[0] for n in neighbors]
        max_sim = max(sims)
        exps = [math.exp(s - max_sim) for s in sims]
        denom = sum(exps) or 1.0
        weights = [e / denom for e in exps]

        weight_by_name: dict[str, float] = {}
        union_aspects: set[AspectID] = set()
        resonance_ceiling = 0.0
        worst_severity = ContradictionSeverity.NONE

        best_idx = max(range(len(neighbors)), key=lambda i: weights[i])
        best_raw = neighbors[best_idx][2]
        best_aspects = neighbors[best_idx][3]
        best_name = str(best_raw.get("name", "UNKNOWN"))
        best_effect_class = EffectClass[best_raw["effect_class"]]

        severity_rank = {
            ContradictionSeverity.NONE: 0,
            ContradictionSeverity.SOFT: 1,
            ContradictionSeverity.HARD: 2,
        }

        for (w, (_sim, key, raw, aspects_fs)) in zip(weights, neighbors, strict=False):
            name = str(raw.get("name", key))
            weight_by_name[name] = weight_by_name.get(name, 0.0) + float(w)
            union_aspects.update(aspects_fs)
            resonance_ceiling += float(raw["resonance_ceiling"]) * float(w)

            if w > 0.10:
                sev = self._contradiction_severity_for_key(key, raw)
                if severity_rank[sev] > severity_rank[worst_severity]:
                    worst_severity = sev

        # Keep aspect pattern compatible with existing seed/registry contracts (1..3).
        if len(union_aspects) > 3:
            union_aspects = set(best_aspects)

        # Polarity from sign balance of the vector components.
        net = 0.0
        for c in vec.components:
            if c > 1e-12:
                net += 1.0
            elif c < -1e-12:
                net -= 1.0
        if net > 0:
            polarity = Polarity.POSITIVE
        elif net < 0:
            polarity = Polarity.NEGATIVE
        else:
            polarity = Polarity.NEUTRAL

        nearest_canonical = best_name
        fluid_name = f"Fluid:{nearest_canonical}"

        # Fingerprint mixes union aspects + vector components for stability.
        fp_basis = (
            "+".join(sorted(a.name for a in union_aspects))
            + "|"
            + ",".join(f"{float(x):.6f}" for x in vec.components[:6])
        )
        semantic_fingerprint = json.dumps(fp_basis).encode("utf-8")
        # Use sha256 via SemanticVector fingerprint style (keep local).
        import hashlib

        fp = hashlib.sha256(semantic_fingerprint).hexdigest()

        return FluidSigil(
            name=fluid_name,
            aspects=frozenset(union_aspects),
            effect_class=best_effect_class,
            resonance_ceiling=float(resonance_ceiling),
            contradiction_severity=worst_severity,
            semantic_fingerprint=fp,
            semantic_vector=vec,
            polarity=polarity,
            source_vector=vector,
            nearest_canonical=nearest_canonical,
            interpolation_weights=weight_by_name,
        )

    def register_sigil_entry(
        self, aspects: frozenset[Aspect], entry: dict, *, allow_override: bool = False
    ) -> None:
        key = self._canonical_key(aspects)
        if key in self._table and not allow_override:
            raise ValueError(
                f"sigil for aspect combination {key!r} already exists; set allow_override=True to replace"
            )
        self._table[key] = entry

    def load_registered_sigils(self, sigils: list[dict]) -> None:
        for row in sigils:
            aspects = row.get("aspects")
            if not isinstance(aspects, frozenset):
                continue
            entry = row.get("entry")
            allow_override = bool(row.get("allow_override", False))
            if not isinstance(entry, dict):
                continue
            self.register_sigil_entry(aspects, entry, allow_override=allow_override)
