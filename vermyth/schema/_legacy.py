import hashlib
import math
from datetime import datetime, timezone
from enum import Enum
from typing import TypeAlias

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


class RegisteredAspect(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=30, pattern="^[A-Z][A-Z0-9_]*$")
    polarity: int
    entropy_coefficient: float = Field(ge=0.0, le=1.0)
    symbol: str = Field(min_length=1, max_length=1)

    @field_validator("polarity")
    @classmethod
    def _valid_polarity(cls, v: int) -> int:
        if v not in (-1, 1):
            raise ValueError("polarity must be -1 or 1")
        return v

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RegisteredAspect):
            return self.name == other.name
        return NotImplemented


Aspect: TypeAlias = AspectID | RegisteredAspect


_REGISTERED_ASPECTS: list[RegisteredAspect] = []
_BASIS_VERSION: int = 0


def full_aspect_order() -> tuple[Aspect, ...]:
    return tuple(ASPECT_CANONICAL_ORDER + tuple(_REGISTERED_ASPECTS))


def registered_aspects() -> list[RegisteredAspect]:
    return list(_REGISTERED_ASPECTS)


def current_basis_version() -> int:
    return int(_BASIS_VERSION)


def _set_basis_version(value: int) -> None:
    global _BASIS_VERSION
    _BASIS_VERSION = max(0, int(value))


def register_aspect(aspect: RegisteredAspect) -> None:
    global _BASIS_VERSION
    if aspect.name in (a.name for a in AspectID):
        raise ValueError(f"Aspect {aspect.name!r} conflicts with canonical AspectID")
    if any(a.name == aspect.name for a in _REGISTERED_ASPECTS):
        raise ValueError(f"Aspect {aspect.name!r} already exists")
    _REGISTERED_ASPECTS.append(aspect)
    _BASIS_VERSION += 1


def _reset_registered_aspects_for_tests() -> None:
    global _BASIS_VERSION
    _REGISTERED_ASPECTS.clear()
    _BASIS_VERSION = 0


class BasisVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = Field(ge=0)
    dimensionality: int = Field(ge=6)
    aspect_order: list[str] = Field(min_length=6)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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


class ChannelStatus(Enum):
    COHERENT = "COHERENT"
    STRAINED = "STRAINED"
    DECOHERENT = "DECOHERENT"


class NodeType(Enum):
    CAST = "CAST"
    FLUID_CAST = "FLUID_CAST"
    AUTO_CAST = "AUTO_CAST"
    GATE = "GATE"
    MERGE = "MERGE"


class ProgramStatus(Enum):
    DRAFT = "DRAFT"
    COMPILED = "COMPILED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GenesisStatus(Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INTEGRATED = "INTEGRATED"


class CausalEdgeType(Enum):
    CAUSES = "CAUSES"
    INHIBITS = "INHIBITS"
    ENABLES = "ENABLES"
    REQUIRES = "REQUIRES"


def _semantic_fingerprint(aspects: frozenset[Aspect]) -> str:
    joined = "+".join(sorted(a.name for a in aspects))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _polarity_from_aspects(aspects: frozenset[Aspect]) -> Polarity:
    net = sum(a.polarity for a in aspects)
    if net > 0:
        return Polarity.POSITIVE
    if net < 0:
        return Polarity.NEGATIVE
    return Polarity.NEUTRAL


class SemanticVector(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    components: tuple[float, ...]
    basis_version: int | None = Field(default=None, ge=0)

    @field_validator("components")
    @classmethod
    def _at_least_six_components(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if len(v) < 6:
            raise ValueError("components must contain at least six floats")
        return tuple(float(x) for x in v)

    @classmethod
    def from_aspects(cls, aspects: frozenset[Aspect]) -> SemanticVector:
        out: list[float] = []
        for aspect in full_aspect_order():
            if aspect in aspects:
                sign = 1.0 if aspect.polarity == 1 else -1.0
                out.append(aspect.entropy_coefficient * sign)
            else:
                out.append(0.0)
        return cls(components=tuple(out), basis_version=current_basis_version())

    def normalized_basis_version(self) -> int:
        if self.basis_version is None:
            return 0
        return int(self.basis_version)

    def upsample_to(self, target_version: int, *, target_dim: int | None = None) -> "SemanticVector":
        target_v = max(0, int(target_version))
        comps = list(self.components)
        if target_dim is not None and int(target_dim) > len(comps):
            comps.extend(0.0 for _ in range(int(target_dim) - len(comps)))
        return SemanticVector(components=tuple(comps), basis_version=target_v)

    def _l2_norm(self) -> float:
        s = 0.0
        for c in self.components:
            s += c * c
        n = math.sqrt(s)
        if not math.isfinite(n):
            return 0.0
        return n

    def cosine_similarity(self, other: SemanticVector) -> float:
        a_basis = self.normalized_basis_version()
        b_basis = other.normalized_basis_version()
        if a_basis != b_basis:
            raise ValueError(
                f"incompatible basis versions: left=v{a_basis} right=v{b_basis}; upsample explicitly first"
            )
        na = self._l2_norm()
        nb = other._l2_norm()
        if na == 0.0 or nb == 0.0:
            return 0.0
        dot = 0.0
        dim = max(len(self.components), len(other.components))
        for i in range(dim):
            a = self.components[i] if i < len(self.components) else 0.0
            b = other.components[i] if i < len(other.components) else 0.0
            dot += a * b
        denom = na * nb
        if denom == 0.0 or not math.isfinite(dot) or not math.isfinite(denom):
            return 0.0
        sim = dot / denom
        if not math.isfinite(sim):
            return 0.0
        if sim > 1.0:
            return 1.0
        if sim < -1.0:
            return -1.0
        return sim

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


class CastNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str = Field(min_length=1, max_length=200)
    node_type: NodeType
    aspects: list[str] | None = None
    vector: SemanticVector | None = None
    intent: Intent
    successors: list[str] = Field(default_factory=list)
    gate_condition: VerdictType | None = None
    merge_strategy: str | None = Field(
        default=None, pattern="^(FIRST_COHERENT|BEST_RESONANCE|ALL)$"
    )

    @model_validator(mode="after")
    def _validate_node_payload(self) -> "CastNode":
        if self.node_type == NodeType.CAST:
            if not self.aspects:
                raise ValueError("CAST nodes require aspects")
            if self.vector is not None:
                raise ValueError("CAST nodes must not define vector")
        elif self.node_type in (NodeType.FLUID_CAST, NodeType.AUTO_CAST):
            if self.vector is None:
                raise ValueError(f"{self.node_type.value} nodes require vector")
            if self.aspects is not None:
                raise ValueError(f"{self.node_type.value} nodes must not define aspects")
        elif self.node_type == NodeType.GATE:
            if self.gate_condition is None:
                raise ValueError("GATE nodes require gate_condition")
        elif self.node_type == NodeType.MERGE:
            if self.merge_strategy is None:
                raise ValueError("MERGE nodes require merge_strategy")
        return self


class SemanticProgram(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    program_id: str = Field(default_factory=lambda: str(ULID()))
    name: str = Field(min_length=1, max_length=200)
    status: ProgramStatus = ProgramStatus.DRAFT
    nodes: list[CastNode] = Field(min_length=1)
    entry_node_ids: list[str] = Field(min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _validate_program_graph(self) -> "SemanticProgram":
        node_ids = {n.node_id for n in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("SemanticProgram contains duplicate node_id values")
        for entry in self.entry_node_ids:
            if entry not in node_ids:
                raise ValueError(f"entry node {entry!r} not found in nodes")
        return self


class ProgramExecution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: str = Field(default_factory=lambda: str(ULID()))
    program_id: str
    status: ProgramStatus
    node_results: dict[str, str] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    branch_id: str = Field(default_factory=lambda: str(ULID()))


class Sigil(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    aspects: frozenset[Aspect] = Field(min_length=1, max_length=3)
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


class ChannelState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    branch_id: str
    cast_count: int = Field(ge=0)
    cumulative_resonance: float = Field(ge=0.0)
    mean_resonance: float = Field(ge=0.0, le=1.0)
    coherence_streak: int = Field(ge=0)
    last_verdict_type: VerdictType
    status: ChannelStatus
    last_cast_id: str
    constraint_vector: SemanticVector | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DivergenceStatus(Enum):
    STABLE = "STABLE"
    DRIFTING = "DRIFTING"
    DIVERGED = "DIVERGED"


class DivergenceThresholds(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    l2_stable_max: float = Field(default=0.30, ge=0.0)
    l2_diverged_min: float = Field(default=0.70, ge=0.0)
    cosine_stable_max: float = Field(default=0.20, ge=0.0, le=2.0)
    cosine_diverged_min: float = Field(default=0.50, ge=0.0, le=2.0)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "DivergenceThresholds":
        if not self.l2_stable_max < self.l2_diverged_min:
            raise ValueError("l2_stable_max must be less than l2_diverged_min")
        if not self.cosine_stable_max < self.cosine_diverged_min:
            raise ValueError("cosine_stable_max must be less than cosine_diverged_min")
        return self


DivergenceThresholds_DEFAULT = DivergenceThresholds()


class DivergenceReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cast_id: str
    parent_cast_id: str
    l2_magnitude: float = Field(ge=0.0)
    cosine_distance: float = Field(ge=0.0, le=2.0)
    status: DivergenceStatus
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    basis_note: str | None = None

    @classmethod
    def classify(
        cls,
        *,
        cast_id: str,
        parent_cast_id: str,
        parent_vector: "SemanticVector",
        child_vector: "SemanticVector",
        thresholds: DivergenceThresholds,
    ) -> "DivergenceReport":
        basis_note: str | None = None
        parent = parent_vector
        child = child_vector
        parent_basis = parent.normalized_basis_version()
        child_basis = child.normalized_basis_version()
        if parent_basis != child_basis:
            target_basis = max(parent_basis, child_basis)
            target_dim = max(len(parent.components), len(child.components))
            parent = parent.upsample_to(target_basis, target_dim=target_dim)
            child = child.upsample_to(target_basis, target_dim=target_dim)
            basis_note = (
                f"basis v{parent_basis} vs v{child_basis} (upsampled to v{target_basis})"
            )
        pc = parent.components
        cc = child.components
        dim = max(len(pc), len(cc))
        l2_sq = 0.0
        for i in range(dim):
            d = float(cc[i] if i < len(cc) else 0.0) - float(pc[i] if i < len(pc) else 0.0)
            l2_sq += d * d
        l2 = math.sqrt(l2_sq)
        cosine_distance = parent.distance(child)
        if cosine_distance < 0.0:
            cosine_distance = 0.0
        elif cosine_distance > 2.0:
            cosine_distance = 2.0

        l2_status: DivergenceStatus
        if l2 < thresholds.l2_stable_max:
            l2_status = DivergenceStatus.STABLE
        elif l2 >= thresholds.l2_diverged_min:
            l2_status = DivergenceStatus.DIVERGED
        else:
            l2_status = DivergenceStatus.DRIFTING

        cos_status: DivergenceStatus
        if cosine_distance < thresholds.cosine_stable_max:
            cos_status = DivergenceStatus.STABLE
        elif cosine_distance >= thresholds.cosine_diverged_min:
            cos_status = DivergenceStatus.DIVERGED
        else:
            cos_status = DivergenceStatus.DRIFTING

        worst = max(
            (l2_status, cos_status),
            key=lambda s: (0 if s == DivergenceStatus.STABLE else 1 if s == DivergenceStatus.DRIFTING else 2),
        )

        return cls(
            cast_id=cast_id,
            parent_cast_id=parent_cast_id,
            l2_magnitude=l2,
            cosine_distance=cosine_distance,
            status=worst,
            basis_note=basis_note,
        )


class PolicyAction(Enum):
    ALLOW = "ALLOW"
    RESHAPE = "RESHAPE"
    DENY = "DENY"


class PolicyThresholds(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_min_resonance: float = Field(default=0.75, ge=0.0, le=1.0)
    reshape_min_resonance: float = Field(default=0.45, ge=0.0, le=1.0)
    max_drift_status: DivergenceStatus = DivergenceStatus.DRIFTING


class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str = Field(default_factory=lambda: str(ULID()))
    action: PolicyAction
    rationale: str = Field(min_length=1, max_length=500)
    cast_id: str
    suggested_intent: Intent | None = None
    parent_cast_id: str | None = None
    divergence_status: DivergenceStatus | None = None
    narrative_coherence: float | None = Field(default=None, ge=0.0, le=1.0)
    thresholds: PolicyThresholds = Field(default_factory=PolicyThresholds)
    model_name: str = Field(default="rule_based", min_length=1, max_length=100)
    model_version: str | None = Field(default="1", max_length=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AutoCastDiagnostics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    steps: list[dict[str, float]] = Field(default_factory=list)
    converged: bool
    final_adjusted: float = Field(ge=0.0, le=1.0)


class CastProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(pattern="^(base|crystallized|fluid)$")
    crystallized_sigil_name: str | None = None
    generation: int | None = Field(default=None, ge=1)
    narrative_coherence: float | None = Field(default=None, ge=0.0, le=1.0)
    causal_root_cast_id: str | None = None


class FluidSigil(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Sigil-compatible fields
    name: str
    aspects: frozenset[Aspect] = Field(min_length=1)
    effect_class: EffectClass
    resonance_ceiling: float = Field(ge=0.0, le=1.0)
    contradiction_severity: ContradictionSeverity
    semantic_fingerprint: str
    semantic_vector: SemanticVector
    polarity: Polarity

    # Fluid-specific metadata
    source_vector: SemanticVector
    nearest_canonical: str
    interpolation_weights: dict[str, float]


class GeometricPacket(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    payload: tuple[float, ...]
    version: int = Field(ge=1)

    @field_validator("payload")
    @classmethod
    def _payload_is_numeric(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(float(x) for x in v)

    @model_validator(mode="after")
    def _validate_shape(self) -> "GeometricPacket":
        # v1 shape: [aspect(>=6)] + [intent(4)] + [lineage_hash(4)] + [proof(1)]
        if self.version != 1:
            raise ValueError("unsupported geometric packet version")
        if len(self.payload) < 6 + 4 + 4 + 1:
            raise ValueError("payload too short for geometric packet v1")
        return self

    def aspect_vector(self) -> SemanticVector:
        return SemanticVector(components=tuple(float(x) for x in self.payload[:6]))

    def intent_encoding(self) -> tuple[float, ...]:
        return tuple(float(x) for x in self.payload[6:10])

    def lineage_hash(self) -> tuple[float, ...]:
        return tuple(float(x) for x in self.payload[10:14])

    def proof_hash(self) -> float:
        return float(self.payload[-1])

    def validate_proof(self, *, epsilon: float = 1e-4) -> bool:
        # v1 proof: dot(first4(aspect), intent4)
        a0, a1, a2, a3 = (float(x) for x in self.payload[:4])
        i0, i1, i2, i3 = (float(x) for x in self.intent_encoding())
        expected = a0 * i0 + a1 * i1 + a2 * i2 + a3 * i3
        return abs(expected - self.proof_hash()) <= epsilon


class GeometricResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict_vector: SemanticVector
    resonance: float = Field(ge=0.0, le=1.0)
    channel_delta: SemanticVector | None = None
    proof_hash: float


class SessionTransport(Enum):
    JSONRPC = "JSONRPC"
    BINARY = "BINARY"


class ProofScheme(Enum):
    HASH = "HASH"
    SIGNED = "SIGNED"


class SessionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REVOKED = "REVOKED"


class PeerIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    peer_id: str = Field(min_length=1, max_length=200)
    key_id: str = Field(min_length=1, max_length=200)
    scheme: ProofScheme
    public_material_ref: str | None = Field(default=None, max_length=500)


class NegotiatedCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    codec_version: int = Field(ge=1)
    aspect_dimensionality: int = Field(ge=6)
    proof_scheme: ProofScheme
    supports_binary: bool = True
    supports_replay_guard: bool = True

    # Optional policy limits (identity-oriented session policy)
    allowed_tools: list[str] | None = None
    max_packet_bytes: int | None = Field(default=None, ge=1)


class SessionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(default_factory=lambda: str(ULID()))
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None
    status: SessionStatus = SessionStatus.OPEN
    transport: SessionTransport
    local_identity: PeerIdentity
    remote_identity: PeerIdentity
    capabilities: NegotiatedCapabilities
    last_sequence: int = Field(default=0, ge=0)
    anchor_cast_id: str | None = None
    channel_branch_id: str | None = None


class CanonicalPacketV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    sequence: int = Field(ge=1)
    packet_type: str = Field(min_length=1, max_length=50)
    payload_hash: str = Field(min_length=64, max_length=64)
    payload: dict
    proof: str = Field(min_length=1, max_length=2048)


class CanonicalResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    sequence: int = Field(ge=1)
    payload_hash: str = Field(min_length=64, max_length=64)
    accepted: bool
    proof: str = Field(min_length=1, max_length=2048)


class SwarmStatus(Enum):
    COHERENT = "COHERENT"
    STRAINED = "STRAINED"
    DECOHERENT = "DECOHERENT"


class SwarmState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    swarm_id: str = Field(default_factory=lambda: str(ULID()))
    consensus_threshold: float = Field(ge=0.0, le=1.0, default=0.75)
    status: SwarmStatus = SwarmStatus.STRAINED
    aggregated_vector: SemanticVector
    last_cast_id: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmergentAspect(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    genesis_id: str = Field(default_factory=lambda: str(ULID()))
    proposed_name: str = Field(min_length=1, max_length=30, pattern="^[A-Z][A-Z0-9_]*$")
    derived_polarity: int
    derived_entropy: float = Field(ge=0.0, le=1.0)
    proposed_symbol: str = Field(min_length=1, max_length=1)
    centroid_vector: SemanticVector
    support_count: int = Field(ge=1)
    mean_resonance: float = Field(ge=0.0, le=1.0)
    coherence_rate: float = Field(ge=0.0, le=1.0)
    status: GenesisStatus = GenesisStatus.PROPOSED
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: datetime | None = None
    evidence_cast_ids: list[str] = Field(default_factory=list)

    @field_validator("derived_polarity")
    @classmethod
    def _valid_polarity(cls, v: int) -> int:
        if v not in (-1, 1):
            raise ValueError("derived_polarity must be -1 or 1")
        return v


class GossipPayload(BaseModel):
    """Federated grimoire sync: signed bundle of seeds and crystallized sigils."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    peer_id: str = Field(min_length=1, max_length=200)
    key_id: str = Field(min_length=1, max_length=200)
    seeds: list[dict] = Field(default_factory=list)
    crystallized: list[dict] = Field(default_factory=list)
    emergent_aspects: list[dict] = Field(default_factory=list)
    proof: str = Field(min_length=64, max_length=64)


class GlyphSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_id: str
    aspect_pattern: frozenset[Aspect] = Field(min_length=1, max_length=3)
    observed_count: int = Field(default=0, ge=0)
    mean_resonance: float = Field(default=0.0, ge=0.0, le=1.0)
    coherence_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    candidate_effect_class: EffectClass | None = None
    crystallized: bool = False
    generation: int = Field(default=1, ge=1)
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


class CrystallizedSigil(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    sigil: Sigil
    source_seed_id: str
    crystallized_at: datetime
    generation: int = Field(default=1, ge=1)


class CausalEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: str = Field(default_factory=lambda: str(ULID()))
    source_cast_id: str
    target_cast_id: str
    edge_type: CausalEdgeType
    weight: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: str | None = Field(default=None, max_length=500)


class CausalQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    root_cast_id: str
    edge_types: list[CausalEdgeType] | None = None
    direction: str = Field(default="both", pattern="^(forward|backward|both)$")
    max_depth: int = Field(default=5, ge=1, le=100)
    min_weight: float = Field(default=0.0, ge=0.0, le=1.0)


class CausalSubgraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    root_cast_id: str
    nodes: list[str] = Field(default_factory=list)
    edges: list[CausalEdge] = Field(default_factory=list)
    narrative_coherence: float = Field(default=0.0, ge=0.0, le=1.0)


class SemanticQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aspect_filter: frozenset[Aspect] | None = None
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
    sigil: Sigil | FluidSigil
    verdict: Verdict
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    immutable: bool = True
    lineage: Lineage | None = None
    glyph_seed_id: str | None = None
    provenance: CastProvenance | None = None

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
