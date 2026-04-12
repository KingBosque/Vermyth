import functools
import json
from pathlib import Path

from vermyth.contracts import EngineContract
from vermyth.schema import (
    ASPECT_CANONICAL_ORDER,
    AspectID,
    CastResult,
    ContradictionSeverity,
    EffectClass,
    GlyphSeed,
    Intent,
    Sigil,
    Verdict,
)


class CompositionEngine(EngineContract):
    """Core engine: composition of AspectID sets into resolved Sigils from JSON tables."""

    @staticmethod
    @functools.cache
    def _canonical_key_cached(aspects: frozenset[AspectID]) -> str:
        order_index = {a: i for i, a in enumerate(ASPECT_CANONICAL_ORDER)}
        ordered = sorted(aspects, key=lambda a: order_index[a])
        return "+".join(a.name for a in ordered)

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = (
            data_dir
            if data_dir is not None
            else Path(__file__).resolve().parent.parent / "data" / "sigils"
        )
        self._table: dict[str, dict] = {}
        self._contradictions: dict[str, dict] = {}
        self._load_table()
        self._load_contradictions()

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
            key = self._canonical_key_cached(aspects_fs)
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

    def _canonical_key(self, aspects: frozenset[AspectID]) -> str:
        return self._canonical_key_cached(aspects)

    def compose(self, aspects: frozenset[AspectID]) -> Sigil:
        n = len(aspects)
        if n < 1:
            raise ValueError("aspects must contain at least one AspectID")
        if n > 3:
            raise ValueError("aspects must contain at most three AspectIDs")
        key = self._canonical_key(aspects)
        if key not in self._table:
            raise ValueError(f"no defined resolution for aspect combination: {key!r}")
        raw = self._table[key]
        contra = self._contradictions.get(key)
        if contra is None:
            contradiction_severity = ContradictionSeverity.NONE
        else:
            sev = contra.get("severity", "NONE")
            contradiction_severity = ContradictionSeverity[sev]
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

    def evaluate(self, sigil: Sigil, intent: Intent) -> Verdict:
        """Implemented in a later module."""
        raise NotImplementedError

    def cast(self, aspects: frozenset[AspectID], intent: Intent) -> CastResult:
        """Implemented in a later module."""
        raise NotImplementedError

    def accumulate(
        self, result: CastResult, seeds: list[GlyphSeed]
    ) -> GlyphSeed | None:
        """Implemented in a later module."""
        raise NotImplementedError

    def crystallize(self, seed: GlyphSeed) -> Sigil | None:
        """Implemented in a later module."""
        raise NotImplementedError
