"""Arcane ontology types that compile to the hardened runtime substrate."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from vermyth.schema import DivergenceStatus, EffectType, RollbackStrategy, SemanticProgram


class WardSpec(BaseModel):
    """Policy overlay: stricter gates for high-stakes coordination."""

    model_config = ConfigDict(extra="forbid")

    allow_min_resonance: float | None = Field(default=None, ge=0.0, le=1.0)
    reshape_min_resonance: float | None = Field(default=None, ge=0.0, le=1.0)
    max_drift_status: DivergenceStatus | None = None
    effect_risk_min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    scorer_weights: dict[str, float] | None = None


class DivinationSpec(BaseModel):
    """Uncertainty / review gate."""

    model_config = ConfigDict(extra="forbid")

    require_causal_context: bool = False
    thresholds: WardSpec | None = None


class BanishmentSpec(BaseModel):
    """Containment: rollback expectations for destructive effects."""

    model_config = ConfigDict(extra="forbid")

    default_rollback: RollbackStrategy = RollbackStrategy.COMPENSATE
    strict: bool = False
    quarantine_effect_types: tuple[EffectType, ...] = Field(
        default=(EffectType.WRITE, EffectType.EXEC, EffectType.NETWORK)
    )


class RitualSpec(BaseModel):
    """Named semantic program (workflow) with arcane provenance."""

    model_config = ConfigDict(extra="forbid")

    ritual_id: str = Field(min_length=1, max_length=120)
    program: SemanticProgram
    ward: WardSpec | None = None
    divination: DivinationSpec | None = None
    banishment: BanishmentSpec | None = None


class RecommendationRule(BaseModel):
    """Single deterministic predicate evaluated against plain tool arguments."""

    model_config = ConfigDict(extra="forbid")

    op: str = Field(
        min_length=1,
        description="Evaluator name (see vermyth.arcane.recommend.RULE_OPS).",
    )
    value: Any = None
    path: str | None = None
    field: str | None = None
    negate: bool = False
    min_len: int | None = Field(default=None, ge=0)
    max_len: int | None = Field(default=None, ge=0)
    rule_id: str | None = None


class RecommendationTier(BaseModel):
    """First matching tier wins for a bundle (tiers are ordered)."""

    model_config = ConfigDict(extra="forbid")

    match_kind: Literal["exact", "strong", "advisory"]
    strength: float = Field(ge=0.0, le=1.0)
    require_all: tuple[RecommendationRule, ...] = Field(default_factory=tuple)


class BundleRecommendationSpec(BaseModel):
    """Inspectable, manifest-declared matching for advisory bundle suggestions."""

    model_config = ConfigDict(extra="forbid")

    target_skills: tuple[str, ...] = Field(
        default=("decide",),
        description="Plain invocations for these tool names are considered.",
    )
    why_better: str = Field(
        min_length=1,
        description="Why prefer semantic_bundle over equivalent plain JSON.",
    )
    tiers: tuple[RecommendationTier, ...] = Field(
        min_length=1,
        description="Ordered; first tier whose rules all pass is used.",
    )


class SemanticBundleManifest(BaseModel):
    """Versioned, reusable bundle: expands to a concrete tool invocation."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=120)
    version: int = Field(ge=1)
    kind: Literal["decide", "cast", "compile_program"]
    template: dict[str, Any]
    param_keys: tuple[str, ...] = Field(default_factory=tuple)
    summary: str | None = None
    description: str | None = None
    recommended_for: tuple[str, ...] = Field(default_factory=tuple)
    stability: Literal["stable", "experimental"] | None = None
    recommendation: BundleRecommendationSpec | None = None


class CompiledInvocation(BaseModel):
    """Output of arcane compilation: plain tool call + provenance."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    input: dict[str, Any]
    arcane_provenance: dict[str, Any] = Field(default_factory=dict)
