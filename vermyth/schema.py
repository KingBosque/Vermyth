import hashlib
import math
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from ulid import ULID


class AspectID(Enum):
    VOID = (-1, 0.95, "◯")
    FORM = (1, 0.15, "⬡")
    MOTION = (1, 0.55, "⟳")
    MIND = (1, 0.35, "◈")
    DECAY = (-1, 0.85, "※")
    LIGHT = (1, 0.05, "✦")

    def __init__(self, polarity: int, entropy_coefficient: float, symbol: str) -> None:
        if polarity not in (-1, 1):
            raise ValueError("polarity must be -1 or 1")
        if not 0.0 <= entropy_coefficient <= 1.0:
            raise ValueError("entropy_coefficient must be between 0.0 and 1.0")
        self.polarity = polarity
        self.entropy_coefficient = entropy_coefficient
        self.symbol = symbol


ASPECT_CANONICAL_ORDER = (
    AspectID.VOID,
    AspectID.FORM,
    AspectID.MOTION,
    AspectID.MIND,
    AspectID.DECAY,
    AspectID.LIGHT,
)


class ContradictionSeverity(Enum):
    NONE = "NONE"
    SOFT = "SOFT"
    HARD = "HARD"


class Polarity(Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class ReversibilityClass(Enum):
    REVERSIBLE = "REVERSIBLE"
    PARTIAL = "PARTIAL"
    IRREVERSIBLE = "IRREVERSIBLE"


class SideEffectTolerance(Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ProjectionMethod(Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"


class VerdictType(Enum):
    COHERENT = "COHERENT"
    PARTIAL = "PARTIAL"
    INCOHERENT = "INCOHERENT"


class EffectClass(Enum):
    ERASURE = "ERASURE"
    MANIFESTATION = "MANIFESTATION"
    FORCE = "FORCE"
    COGNITION = "COGNITION"
    DISSOLUTION = "DISSOLUTION"
    REVELATION = "REVELATION"
    CONTAINMENT = "CONTAINMENT"
    NEGATION = "NEGATION"
    CORRUPTION = "CORRUPTION"
    ACCELERATION = "ACCELERATION"
    BINDING = "BINDING"
    EMERGENCE = "EMERGENCE"


def _semantic_fingerprint(aspects: frozenset[AspectID]) -> str:
    joined = "+".join(sorted(a.name for a in aspects))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _polarity_from_aspects(aspects: frozenset[AspectID]) -> Polarity:
    net = sum(a.polarity for a in aspects)
    if net > 0:
        return Polarity.POSITIVE
    if net < 0:
        return Polarity.NEGATIVE
    return Polarity.NEUTRAL


class SemanticVector(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    components: tuple[float, float, float, float, float, float]

    @field_validator("components")
    @classmethod
    def _exactly_six_components(
        cls, v: tuple[float, ...]
    ) -> tuple[float, float, float, float, float, float]:
        if len(v) != 6:
            raise ValueError("components must contain exactly six floats")
        return (
            float(v[0]),
            float(v[1]),
            float(v[2]),
            float(v[3]),
            float(v[4]),
            float(v[5]),
        )

    @classmethod
    def from_aspects(cls, aspects: frozenset[AspectID]) -> SemanticVector:
        out: list[float] = []
        for aspect in ASPECT_CANONICAL_ORDER:
            if aspect in aspects:
                sign = 1.0 if aspect.polarity == 1 else -1.0
                out.append(aspect.entropy_coefficient * sign)
            else:
                out.append(0.0)
        return cls(components=(out[0], out[1], out[2], out[3], out[4], out[5]))

    def _l2_norm(self) -> float:
        s = 0.0
        for c in self.components:
            s += c * c
        return math.sqrt(s)

    def cosine_similarity(self, other: SemanticVector) -> float:
        na = self._l2_norm()
        nb = other._l2_norm()
        if na == 0.0 or nb == 0.0:
            return 0.0
        dot = 0.0
        for i in range(6):
            dot += self.components[i] * other.components[i]
        return dot / (na * nb)

    def distance(self, other: SemanticVector) -> float:
        return 1.0 - self.cosine_similarity(other)


class IntentVector(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    vector: SemanticVector
    projection_method: ProjectionMethod
    constraint_component: SemanticVector
    semantic_component: SemanticVector | None
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_projection_consistency(self) -> IntentVector:
        if self.projection_method == ProjectionMethod.FULL:
            if self.semantic_component is None:
                raise ValueError(
                    "semantic_component is required when projection_method is FULL"
                )
        elif self.projection_method == ProjectionMethod.PARTIAL:
            if self.confidence > 0.65:
                raise ValueError(
                    "confidence must be at most 0.65 when projection_method is PARTIAL"
                )
        return self


def _normalize_semantic_vector(value: object) -> SemanticVector:
    if isinstance(value, SemanticVector):
        return value
    if isinstance(value, dict):
        return SemanticVector.model_validate(value)
    raise TypeError("semantic_vector must be SemanticVector or dict")


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(max_length=500)
    scope: str = Field(max_length=200)
    reversibility: ReversibilityClass
    side_effect_tolerance: SideEffectTolerance


class Sigil(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    aspects: frozenset[AspectID] = Field(min_length=1, max_length=3)
    effect_class: EffectClass
    resonance_ceiling: float = Field(ge=0.0, le=1.0)
    contradiction_severity: ContradictionSeverity
    semantic_fingerprint: str
    semantic_vector: SemanticVector
    polarity: Polarity

    @model_validator(mode="before")
    @classmethod
    def _derive_sigil_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        raw_aspects = payload.get("aspects")
        if raw_aspects is None:
            return payload
        aspects = frozenset(raw_aspects)
        expected_fp = _semantic_fingerprint(aspects)
        expected_vec = SemanticVector.from_aspects(aspects)
        expected_pol = _polarity_from_aspects(aspects)
        if (
            payload.get("semantic_fingerprint") is not None
            and payload["semantic_fingerprint"] != expected_fp
        ):
            raise ValueError("semantic_fingerprint does not match aspects")
        if payload.get("semantic_vector") is not None:
            got = _normalize_semantic_vector(payload["semantic_vector"])
            if got.components != expected_vec.components:
                raise ValueError("semantic_vector does not match aspects")
        if payload.get("polarity") is not None and payload["polarity"] != expected_pol:
            raise ValueError("polarity does not match aspects")
        payload["semantic_fingerprint"] = expected_fp
        payload["semantic_vector"] = expected_vec
        payload["polarity"] = expected_pol
        return payload


class ResonanceScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: float = Field(ge=0.0, le=1.0)
    adjusted: float = Field(ge=0.0, le=1.0)
    ceiling_applied: bool
    proof: str = Field(max_length=300)


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict_type: VerdictType
    resonance: ResonanceScore
    effect_description: str = Field(max_length=300)
    incoherence_reason: str | None
    casting_note: str = Field(max_length=200)
    intent_vector: IntentVector


class Lineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parent_cast_id: str
    depth: int = Field(ge=1)
    branch_id: str
    divergence_vector: SemanticVector | None = None

    @model_validator(mode="before")
    @classmethod
    def _default_branch_id(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if payload.get("branch_id") is None:
            payload["branch_id"] = str(ULID())
        return payload


class GlyphSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_id: str
    aspect_pattern: frozenset[AspectID] = Field(min_length=1, max_length=3)
    observed_count: int = Field(default=0, ge=0)
    mean_resonance: float = Field(default=0.0, ge=0.0, le=1.0)
    coherence_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    candidate_effect_class: EffectClass | None = None
    crystallized: bool = False
    semantic_vector: SemanticVector

    @model_validator(mode="before")
    @classmethod
    def _seed_id_and_vector(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if "seed_id" in data:
            raise ValueError("seed_id must not be supplied; it is generated at instantiation")
        payload = dict(data)
        raw_pattern = payload.get("aspect_pattern")
        if raw_pattern is None:
            return payload
        pattern = frozenset(raw_pattern)
        expected_vec = SemanticVector.from_aspects(pattern)
        if payload.get("semantic_vector") is not None:
            got = _normalize_semantic_vector(payload["semantic_vector"])
            if got.components != expected_vec.components:
                raise ValueError("semantic_vector does not match aspect_pattern")
        payload["seed_id"] = str(ULID())
        payload["semantic_vector"] = expected_vec
        return payload


class SemanticQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aspect_filter: frozenset[AspectID] | None = None
    verdict_filter: VerdictType | None = None
    min_resonance: float | None = Field(default=None, ge=0.0, le=1.0)
    effect_class_filter: EffectClass | None = None
    branch_id: str | None = None
    proximity_to: SemanticVector | None = None
    proximity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _proximity_requires_vector(self) -> SemanticQuery:
        if self.proximity_threshold is not None and self.proximity_to is None:
            raise ValueError("proximity_to is required when proximity_threshold is set")
        return self


class CastResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cast_id: str = Field(default_factory=lambda: str(ULID()))
    intent: Intent
    sigil: Sigil
    verdict: Verdict
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    immutable: bool = True
    lineage: Lineage | None = None
    glyph_seed_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_generated_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if "cast_id" in data:
            raise ValueError("cast_id must not be supplied; it is generated at instantiation")
        if "timestamp" in data:
            raise ValueError("timestamp must not be supplied; it is generated at instantiation")
        if "immutable" in data:
            raise ValueError("immutable must not be supplied; it is fixed at instantiation")
        return data

    def model_post_init(self, __context: object) -> None:
        object.__setattr__(self, "_vermyth_castresult_locked", True)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_vermyth_castresult_locked":
            return object.__setattr__(self, name, value)
        if getattr(self, "_vermyth_castresult_locked", False):
            raise ValueError("CastResult cannot be mutated after instantiation")
        super().__setattr__(name, value)
