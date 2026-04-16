import os
from typing import Optional

from vermyth.contracts import (
    CompositionContract,
    EvaluationContract,
    GrimoireContract,
    ProjectionBackend,
)
from vermyth.engine.policy.base import PolicyModel
from vermyth.engine.policy.rule_based import RuleBasedPolicyModel
from vermyth.engine.operations import cast as cast_ops
from vermyth.engine.operations import casting as casting_ops
from vermyth.engine.operations import causal as causal_ops
from vermyth.engine.operations import decisions as decision_ops
from vermyth.engine.operations import drift as drift_ops
from vermyth.engine.operations import genesis as genesis_ops
from vermyth.engine.operations import intent as intent_ops
from vermyth.engine.operations import programs as program_ops
from vermyth.engine.operations import seeds as seed_ops
from vermyth.engine.operations import swarm as swarm_ops
from vermyth.registry import AspectRegistry
from vermyth.schema import (
    Aspect,
    AspectID,
    AutoCastDiagnostics,
    CastNode,
    CastResult,
    CausalEdge,
    CausalQuery,
    CausalSubgraph,
    ChannelState,
    ChannelStatus,
    ContradictionSeverity,
    DivergenceReport,
    DivergenceStatus,
    EmergentAspect,
    EffectClass,
    FluidSigil,
    GlyphSeed,
    Intent,
    IntentVector,
    Lineage,
    ProjectionMethod,
    ProgramExecution,
    PolicyAction,
    PolicyDecision,
    PolicyThresholds,
    ReversibilityClass,
    ResonanceScore,
    SemanticProgram,
    SemanticVector,
    SideEffectTolerance,
    Sigil,
    Verdict,
    VerdictType,
)

_CASTING_NOTE_FALLBACK = cast_ops._CASTING_NOTE_FALLBACK
_CASTING_NOTES = cast_ops._CASTING_NOTES

_REVERSIBILITY_PRESSURES: dict[ReversibilityClass, tuple[float, ...]] = {
    ReversibilityClass.IRREVERSIBLE: (0.80, -0.40, 0.0, 0.0, 0.70, -0.30),
    ReversibilityClass.PARTIAL: (0.0, 0.0, 0.30, 0.20, 0.0, 0.0),
    ReversibilityClass.REVERSIBLE: (-0.50, 0.70, 0.0, 0.0, -0.40, 0.60),
}

_SIDE_EFFECT_PRESSURES: dict[SideEffectTolerance, tuple[float, ...]] = {
    SideEffectTolerance.NONE: (-0.60, 0.60, 0.0, 0.0, -0.50, 0.50),
    SideEffectTolerance.LOW: (-0.20, 0.30, 0.0, 0.30, -0.20, 0.0),
    SideEffectTolerance.MEDIUM: (0.0, 0.0, 0.20, 0.20, 0.0, 0.0),
    SideEffectTolerance.HIGH: (0.40, -0.30, 0.30, 0.0, 0.50, 0.0),
}


def _canonical_aspect_key(aspects: frozenset[Aspect]) -> str:
    order_index = {a: i for i, a in enumerate(AspectRegistry.get().full_order)}
    ordered = sorted(aspects, key=lambda a: order_index.get(a, 10**9))
    return "+".join(a.name for a in ordered)


def _log_stderr(message: str) -> None:
    os.write(2, (message + "\n").encode("utf-8", errors="replace"))


class ChannelDecoherentError(RuntimeError):
    pass


class ResonanceEngine(EvaluationContract):
    """Resonance evaluation: project intent, score against sigil, verdict, cast lifecycle."""

    def __init__(
        self,
        composition_engine: CompositionContract,
        backend: Optional[ProjectionBackend] = None,
        *,
        contradictions: dict[str, dict] | None = None,
        policy_model: PolicyModel | None = None,
    ) -> None:
        self.composition_engine = composition_engine
        self.backend = backend
        self._contradictions: Optional[dict[str, dict]] = contradictions
        self._policy_model: PolicyModel = policy_model or RuleBasedPolicyModel()

    def _load_contradictions(self) -> dict[str, dict]:
        return cast_ops.load_contradictions(self)

    def _clip_component(self, x: float) -> float:
        return intent_ops.clip_component(x)

    def _normalize_unit(self, components: tuple[float, ...]) -> SemanticVector:
        return intent_ops.normalize_unit(components)

    def _build_constraint_vector(self, intent: Intent) -> SemanticVector:
        return intent_ops.build_constraint_vector(self, intent)

    def _build_semantic_vector(self, intent: Intent) -> Optional[SemanticVector]:
        return intent_ops.build_semantic_vector(self, intent)

    def _combine_vectors(
        self, constraint: SemanticVector, semantic: Optional[SemanticVector]
    ) -> tuple[SemanticVector, ProjectionMethod, float]:
        return intent_ops.combine_vectors(self, constraint, semantic)

    def _build_intent_vector(self, intent: Intent) -> IntentVector:
        return intent_ops.build_intent_vector(self, intent)

    def _evaluate_with_intent_vector(
        self, sigil: Sigil | FluidSigil, intent: Intent, intent_vector: IntentVector
    ) -> Verdict:
        return intent_ops.evaluate_with_intent_vector(self, sigil, intent, intent_vector)

    def _alignment_word(self, cosine: float) -> str:
        return intent_ops.alignment_word(cosine)

    def _penalty_phrase(self, severity: ContradictionSeverity) -> str:
        return intent_ops.penalty_phrase(severity)

    def _compute_resonance(
        self, sigil: Sigil | FluidSigil, intent_vector: IntentVector
    ) -> tuple[ResonanceScore, float]:
        return cast_ops.compute_resonance(self, sigil, intent_vector)

    def _verdict_type(self, adjusted: float) -> VerdictType:
        return cast_ops.verdict_type(adjusted)

    def _casting_note(
        self, sigil: Sigil | FluidSigil, verdict_type: VerdictType, intent_vector: IntentVector
    ) -> str:
        return cast_ops.casting_note(sigil, verdict_type, intent_vector)

    def _effect_description(self, sigil: Sigil | FluidSigil, verdict_type: VerdictType) -> str:
        return cast_ops.effect_description(sigil, verdict_type)

    def _incoherence_reason(
        self,
        sigil: Sigil | FluidSigil,
        verdict_type: VerdictType,
        cosine: float,
    ) -> Optional[str]:
        return cast_ops.incoherence_reason(self, sigil, verdict_type, cosine)

    def evaluate(self, sigil: Sigil | FluidSigil, intent: Intent) -> Verdict:
        return cast_ops.evaluate(self, sigil, intent)

    def cast(self, aspects: frozenset[AspectID], intent: Intent) -> CastResult:
        return casting_ops.cast(self, aspects, intent)

    def fluid_cast(self, vector: SemanticVector, intent: Intent) -> CastResult:
        return casting_ops.fluid_cast(self, vector, intent)

    def _blend_toward(
        self, current: SemanticVector, target: SemanticVector, alpha: float
    ) -> SemanticVector:
        return cast_ops.blend_toward(self, current, target, alpha)

    def auto_cast(
        self,
        vector: SemanticVector,
        intent: Intent,
        *,
        max_depth: int = 5,
        target_resonance: float = 0.75,
        blend_alpha: float = 0.35,
        with_diagnostics: bool = False,
    ) -> tuple[CastResult, list[CastResult]] | tuple[CastResult, list[CastResult], AutoCastDiagnostics]:
        return casting_ops.auto_cast(
            self,
            vector,
            intent,
            max_depth=max_depth,
            target_resonance=target_resonance,
            blend_alpha=blend_alpha,
            with_diagnostics=with_diagnostics,
        )

    def _cast_result_with_lineage(
        self, base: CastResult, parent: CastResult, branch_id: str
    ) -> CastResult:
        return cast_ops.cast_result_with_lineage(self, base, parent, branch_id)

    def _topological_order(
        self, nodes: dict[str, CastNode], predecessors: dict[str, list[str]]
    ) -> list[str]:
        return program_ops.topological_order(self, nodes, predecessors)

    def compile_program(self, program: SemanticProgram) -> SemanticProgram:
        return program_ops.compile_program(self, program)

    def execute_program(self, program: SemanticProgram) -> ProgramExecution:
        return program_ops.execute_program(self, program)

    def propose_genesis(
        self,
        cast_history: list[CastResult],
        *,
        min_cluster_size: int = 15,
        min_unexplained_variance: float = 0.3,
    ) -> list[EmergentAspect]:
        return genesis_ops.propose_genesis(
            self,
            cast_history,
            min_cluster_size=min_cluster_size,
            min_unexplained_variance=min_unexplained_variance,
        )

    def infer_causal_edge(
        self, source: CastResult, target: CastResult
    ) -> CausalEdge | None:
        return causal_ops.infer_causal_edge(self, source, target)

    def evaluate_narrative(self, edges: list[CausalEdge]) -> float:
        return causal_ops.evaluate_narrative(self, edges)

    def predictive_cast(self, graph: CausalSubgraph, intent: Intent) -> CastResult:
        return causal_ops.predictive_cast(self, graph, intent)

    def decide(
        self,
        intent: Intent,
        *,
        aspects: frozenset[AspectID] | None = None,
        vector: SemanticVector | None = None,
        parent_cast_id: str | None = None,
        causal_root_cast_id: str | None = None,
        thresholds: PolicyThresholds | None = None,
        grimoire: GrimoireContract | None = None,
    ) -> tuple[PolicyDecision, CastResult]:
        return decision_ops.decide(
            self,
            intent,
            aspects=aspects,
            vector=vector,
            parent_cast_id=parent_cast_id,
            causal_root_cast_id=causal_root_cast_id,
            thresholds=thresholds,
            grimoire=grimoire,
        )

    def swarm_cast(
        self,
        intent: Intent,
        members: list[tuple[str, SemanticVector, int]],
        *,
        consensus_threshold: float = 0.75,
    ) -> tuple[CastResult, SemanticVector, str, dict[str, int]]:
        return swarm_ops.swarm_cast(
            self,
            intent,
            members,
            consensus_threshold=consensus_threshold,
        )

    def chained_cast(
        self,
        aspects: frozenset[AspectID],
        intent: Intent,
        channel: ChannelState | None,
        *,
        force: bool = False,
    ) -> tuple[CastResult, ChannelState]:
        return swarm_ops.chained_cast(
            self,
            aspects,
            intent,
            channel,
            force=force,
        )

    def sync_channel(self, channel: ChannelState, seeds: list[GlyphSeed]) -> ChannelState:
        return drift_ops.sync_channel(self, channel, seeds)

    def accumulate(
        self, result: CastResult, seeds: list[GlyphSeed]
    ) -> Optional[GlyphSeed]:
        return seed_ops.accumulate(self, result, seeds)

    def crystallize(self, seed: GlyphSeed) -> Optional[Sigil]:
        return seed_ops.crystallize(self, seed)
