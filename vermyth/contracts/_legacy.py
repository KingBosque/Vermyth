from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from vermyth.schema import (
    BasisVersion,
    Aspect,
    AspectID,
    CastResult,
    ChannelState,
    ContradictionSeverity,
    CanonicalPacketV2,
    CanonicalResponseV2,
    CausalEdge,
    CausalQuery,
    CausalSubgraph,
    CrystallizedSigil,
    EmergentAspect,
    EffectClass,
    FluidSigil,
    GlyphSeed,
    Intent,
    SessionRecord,
    RegisteredAspect,
    SemanticQuery,
    SemanticProgram,
    SemanticVector,
    Sigil,
    ProgramExecution,
    SwarmState,
    GossipPayload,
    PolicyDecision,
    PolicyThresholds,
    PolicyAction,
    Verdict,
)

# -----------------------------------------------------------------------------
# Section 1: Engine
# -----------------------------------------------------------------------------


class CompositionContract(ABC):
    """Abstract contract for composing AspectIDs into Sigils."""

    @abstractmethod
    def compose(self, aspects: frozenset[AspectID]) -> Sigil:
        """Compose a set of AspectIDs into a resolved Sigil.

        Aspects must contain between 1 and 3 members inclusive. Raises ValueError
        if aspects is empty or exceeds 3 members. Raises ValueError if the aspect
        combination has no defined resolution. Returns a fully populated Sigil
        with auto-computed semantic_fingerprint, semantic_vector, and polarity.
        """
        ...

    @abstractmethod
    def register_sigil_entry(
        self, aspects: frozenset[Aspect], entry: dict, *, allow_override: bool = False
    ) -> None:
        """Register or override a sigil entry for an aspect combination.

        Raises ValueError if an entry already exists and allow_override is False.
        """
        ...

    @abstractmethod
    def load_registered_sigils(self, sigils: list[dict]) -> None:
        """Load previously registered sigil overrides/extensions into the composition table."""
        ...

    @abstractmethod
    def interpolate(self, vector: SemanticVector, k: int = 3) -> FluidSigil:
        """Interpolate a raw semantic vector into a FluidSigil.

        Uses the current composition table as anchors, selecting the top-k
        canonical sigils by similarity and producing a FluidSigil with
        interpolation_weights and derived ceiling/severity metadata.
        """
        ...


class EvaluationContract(ABC):
    """Abstract contract for evaluating and casting Sigils against Intent."""

    @abstractmethod
    def evaluate(self, sigil: Sigil, intent: Intent) -> Verdict:
        """Evaluate coherence between a resolved Sigil and a declared Intent.

        Computes a ResonanceScore by comparing the sigil's semantic_vector
        against the intent's declared properties. Applies the sigil's
        resonance_ceiling as an upper bound on the adjusted score. Returns a
        Verdict with verdict_type COHERENT if adjusted resonance >= 0.75, PARTIAL
        if >= 0.45, INCOHERENT otherwise. Never raises — always returns a
        Verdict regardless of input quality.
        """
        ...

    @abstractmethod
    def cast(self, aspects: frozenset[AspectID], intent: Intent) -> CastResult:
        """Compose aspects into a Sigil and evaluate against Intent in one step.

        Equivalent to calling compose then evaluate then constructing a
        CastResult. Raises ValueError if compose raises. Returns a fully
        populated immutable CastResult with auto-generated cast_id and timestamp.
        """
        ...

    @abstractmethod
    def accumulate(
        self, result: CastResult, seeds: list[GlyphSeed]
    ) -> Optional[GlyphSeed]:
        """Update or create a GlyphSeed after a cast.

        After a cast, update the GlyphSeed matching this result's sigil aspect
        pattern if one exists in seeds, or create a new one. Updates
        observed_count, mean_resonance as a running mean, and coherence_rate as
        proportion of COHERENT verdicts. Returns the updated or created GlyphSeed.
        Returns None if result is INCOHERENT and no existing seed matches.
        """
        ...

    @abstractmethod
    def crystallize(self, seed: GlyphSeed) -> Optional[Sigil]:
        """Promote a GlyphSeed into a named Sigil when thresholds are met.

        Crystallization requires: observed_count >= 10, mean_resonance >= 0.70,
        coherence_rate >= 0.65, crystallized is False. If requirements are not
        met returns None. If requirements are met returns a new Sigil derived
        from the seed's aspect_pattern and candidate_effect_class. The caller is
        responsible for persisting the result. Never mutates the seed directly —
        the caller must update crystallized via the grimoire.
        """
        ...

    @abstractmethod
    def fluid_cast(self, vector: SemanticVector, intent: Intent) -> CastResult:
        """Interpolate a FluidSigil from a raw vector and evaluate it against intent."""
        ...

    @abstractmethod
    def chained_cast(
        self,
        aspects: frozenset[AspectID],
        intent: Intent,
        channel: ChannelState | None,
        *,
        force: bool = False,
    ) -> tuple[CastResult, ChannelState]:
        """Cast with channel continuity constraints, returning updated channel state."""
        ...

    @abstractmethod
    def sync_channel(self, channel: ChannelState, seeds: list[GlyphSeed]) -> ChannelState:
        """Recover a decoherent channel using crystallization-derived constraints."""
        ...

    @abstractmethod
    def auto_cast(
        self,
        vector: SemanticVector,
        intent: Intent,
        *,
        max_depth: int = 5,
        target_resonance: float = 0.75,
        blend_alpha: float = 0.35,
    ) -> tuple[CastResult, list[CastResult]]:
        """Self-healing fluid casts: iteratively refine vector until coherent or max_depth."""
        ...

    @abstractmethod
    def swarm_cast(
        self,
        intent: Intent,
        members: list[tuple[str, SemanticVector, int]],
        *,
        consensus_threshold: float = 0.75,
    ) -> tuple[CastResult, SemanticVector, str, dict[str, int]]:
        """Aggregate weighted peer vectors, fluid-cast, return new coherence streaks per session."""
        ...

    @abstractmethod
    def compile_program(self, program: SemanticProgram) -> SemanticProgram:
        """Validate and normalize a semantic program graph."""
        ...

    @abstractmethod
    def execute_program(self, program: SemanticProgram) -> ProgramExecution:
        """Execute a compiled semantic program and return execution metadata."""
        ...

    @abstractmethod
    def propose_genesis(
        self,
        cast_history: list[CastResult],
        *,
        min_cluster_size: int = 15,
        min_unexplained_variance: float = 0.3,
    ) -> list[EmergentAspect]:
        """Propose emergent aspects from coherent cast history."""
        ...

    @abstractmethod
    def infer_causal_edge(
        self, source: CastResult, target: CastResult
    ) -> CausalEdge | None:
        """Infer a typed causal edge between two cast results."""
        ...

    @abstractmethod
    def evaluate_narrative(self, edges: list[CausalEdge]) -> float:
        """Score causal chain coherence for a set of typed edges."""
        ...

    @abstractmethod
    def predictive_cast(self, graph: CausalSubgraph, intent: Intent) -> CastResult:
        """Predict a coherence-improving cast using causal history."""
        ...

    @abstractmethod
    def decide(
        self,
        intent: Intent,
        *,
        aspects: frozenset[AspectID] | None = None,
        vector: SemanticVector | None = None,
        parent_cast_id: str | None = None,
        causal_root_cast_id: str | None = None,
        thresholds: PolicyThresholds | None = None,
        grimoire: "GrimoireContract | None" = None,
    ) -> tuple[PolicyDecision, CastResult]:
        """Evaluate and return a policy action plus the supporting cast."""
        ...


class EngineContract(CompositionContract, EvaluationContract, ABC):
    """Backward-compatible engine super-contract (compose + evaluate + lifecycle)."""

# -----------------------------------------------------------------------------
# Section 2: Grimoire
# -----------------------------------------------------------------------------


class GrimoireContract(ABC):
    """Abstract contract for persistent cast and seed storage."""

    @abstractmethod
    def write(self, result: CastResult) -> None:
        """Persist a CastResult to the grimoire.

        Raises ValueError if a CastResult with the same cast_id already exists.
        Raises RuntimeError if the underlying store is unavailable.
        """
        ...

    @abstractmethod
    def read(self, cast_id: str) -> CastResult:
        """Retrieve a single CastResult by cast_id.

        Raises KeyError if cast_id is not found. Raises RuntimeError if the
        underlying store is unavailable.
        """
        ...

    @abstractmethod
    def query(self, query: SemanticQuery) -> list[CastResult]:
        """Retrieve CastResults matching structured field filters.

        Applies aspect_filter, verdict_filter, min_resonance,
        effect_class_filter, and branch_id filters if present. Ignores
        proximity_to and proximity_threshold — those belong to semantic_search.
        Returns up to query.limit results ordered by timestamp descending.
        Returns empty list if no results match.
        """
        ...

    @abstractmethod
    def semantic_search(self, query: SemanticQuery) -> list[CastResult]:
        """Retrieve CastResults by semantic proximity.

        Requires query.proximity_to and query.proximity_threshold to be set —
        raises ValueError otherwise. Computes cosine similarity between
        query.proximity_to and each stored CastResult's sigil.semantic_vector.
        Returns results where similarity >= proximity_threshold, ordered by
        similarity descending, up to query.limit. Returns empty list if no
        results meet threshold.
        """
        ...

    @abstractmethod
    def write_seed(self, seed: GlyphSeed) -> None:
        """Persist a GlyphSeed.

        If a seed with the same seed_id exists, replace it. Raises RuntimeError
        if the underlying store is unavailable.
        """
        ...

    @abstractmethod
    def read_seed(self, seed_id: str) -> GlyphSeed:
        """Retrieve a GlyphSeed by seed_id.

        Raises KeyError if not found. Raises RuntimeError if the underlying
        store is unavailable.
        """
        ...

    @abstractmethod
    def query_seeds(
        self,
        aspect_pattern: Optional[frozenset[Aspect]],
        crystallized: Optional[bool],
    ) -> list[GlyphSeed]:
        """Retrieve GlyphSeeds filtered by aspect pattern and crystallized flag.

        Returns all seeds if both filters are None. Returns empty list if no
        seeds match.
        """
        ...

    @abstractmethod
    def write_crystallized_sigil(self, crystal: CrystallizedSigil) -> None:
        """Persist a crystallized Sigil snapshot.

        If a row with the same name exists, replace it. Raises RuntimeError if
        the underlying store is unavailable.
        """
        ...

    @abstractmethod
    def read_crystallized_sigil(self, name: str) -> CrystallizedSigil:
        """Retrieve a crystallized Sigil by name.

        Raises KeyError if name is not found.
        """
        ...

    @abstractmethod
    def crystallized_for_aspects(
        self, aspects: frozenset[Aspect]
    ) -> CrystallizedSigil | None:
        """Return most recent crystallized Sigil for aspects, or None."""
        ...

    @abstractmethod
    def query_crystallized_sigils(self) -> list[CrystallizedSigil]:
        """List crystallized Sigils ordered newest-first."""
        ...

    @abstractmethod
    def write_channel_state(self, state: ChannelState) -> None:
        """Persist a ChannelState snapshot for a branch."""
        ...

    @abstractmethod
    def read_channel_state(self, branch_id: str) -> ChannelState:
        """Read ChannelState for a branch, raising KeyError if missing."""
        ...

    @abstractmethod
    def query_channel_states(self, status: Optional[str], limit: int) -> list[ChannelState]:
        """List ChannelStates optionally filtered by status."""
        ...

    @abstractmethod
    def write_session(self, session: SessionRecord) -> None:
        """Persist a SessionRecord."""
        ...

    @abstractmethod
    def read_session(self, session_id: str) -> SessionRecord:
        """Read SessionRecord by session_id."""
        ...

    @abstractmethod
    def close_session(self, session_id: str) -> SessionRecord:
        """Close a session (mark CLOSED and set closed_at)."""
        ...

    @abstractmethod
    def advance_session_sequence(self, session_id: str, new_sequence: int) -> SessionRecord:
        """Monotonically advance last_sequence for replay protection."""
        ...

    @abstractmethod
    def write_session_packet(self, packet: CanonicalPacketV2) -> None:
        """Persist an inbound canonical packet for a session."""
        ...

    @abstractmethod
    def write_session_response(self, response: CanonicalResponseV2) -> None:
        """Persist an outbound canonical response for a session."""
        ...

    @abstractmethod
    def query_session_packets(self, session_id: str, limit: int) -> list[CanonicalPacketV2]:
        """List session packets ordered by sequence ascending."""
        ...

    @abstractmethod
    def query_session_responses(self, session_id: str, limit: int) -> list[CanonicalResponseV2]:
        """List session responses ordered by sequence ascending."""
        ...

    @abstractmethod
    def write_registered_aspect(self, aspect: RegisteredAspect, ordinal: int) -> None:
        """Persist a newly registered Aspect.

        Raises ValueError if an Aspect with the same name already exists.
        """
        ...

    @abstractmethod
    def query_registered_aspects(self) -> list[tuple[RegisteredAspect, int]]:
        """Return registered Aspects in ordinal order."""
        ...

    @abstractmethod
    def write_basis_version(self, basis: BasisVersion) -> None:
        """Persist a basis version snapshot."""
        ...

    @abstractmethod
    def read_basis_version(self, version: int) -> BasisVersion:
        """Read a basis version by exact id."""
        ...

    @abstractmethod
    def read_latest_basis_version(self) -> BasisVersion:
        """Read the latest basis version snapshot."""
        ...

    @abstractmethod
    def write_registered_sigil(
        self,
        name: str,
        aspects: list[str],
        effect_class: str,
        resonance_ceiling: float,
        contradiction_severity: str,
        is_override: bool,
    ) -> None:
        """Persist a registered Sigil override/extension."""
        ...

    @abstractmethod
    def read_registered_sigil(self, name: str) -> dict:
        """Retrieve a registered Sigil by name.

        Raises KeyError if name not found.
        """
        ...

    @abstractmethod
    def query_registered_sigils(self) -> list[dict]:
        """List registered Sigils ordered newest-first."""
        ...

    @abstractmethod
    def write_divergence_report(self, report: "DivergenceReport") -> None:
        """Persist a divergence analysis report for a cast."""
        ...

    @abstractmethod
    def read_divergence_report(self, cast_id: str) -> "DivergenceReport":
        """Retrieve a divergence analysis report by cast_id.

        Raises KeyError if cast_id is not found.
        """
        ...

    @abstractmethod
    def query_divergence_reports(
        self,
        status: Optional["DivergenceStatus"],
        limit: int,
        *,
        since: datetime | None = None,
    ) -> list["DivergenceReport"]:
        """List divergence reports ordered newest-first."""
        ...

    @abstractmethod
    def write_divergence_thresholds(self, thresholds: "DivergenceThresholds") -> None:
        """Persist divergence thresholds used for classification."""
        ...

    @abstractmethod
    def read_divergence_thresholds(self) -> "DivergenceThresholds":
        """Read active divergence thresholds, returning defaults if unset."""
        ...

    @abstractmethod
    def write_swarm_state(self, state: SwarmState) -> None:
        """Persist swarm aggregate status and metadata."""
        ...

    @abstractmethod
    def read_swarm_state(self, swarm_id: str) -> SwarmState:
        """Read swarm by id."""
        ...

    @abstractmethod
    def upsert_swarm_member(
        self,
        swarm_id: str,
        session_id: str,
        vector: SemanticVector,
        coherence_streak: int,
    ) -> None:
        """Insert or update a swarm member row."""
        ...

    @abstractmethod
    def query_swarm_members(self, swarm_id: str) -> list[tuple[str, SemanticVector, int]]:
        """Return (session_id, last_vector, coherence_streak) for each member."""
        ...

    @abstractmethod
    def apply_gossip_sync(self, payload: GossipPayload) -> dict[str, Any]:
        """Verify federation HMAC and merge seeds and crystallized sigils."""
        ...

    @abstractmethod
    def write_program(self, program: SemanticProgram) -> None:
        """Persist a semantic program definition."""
        ...

    @abstractmethod
    def read_program(self, program_id: str) -> SemanticProgram:
        """Read a semantic program by id."""
        ...

    @abstractmethod
    def query_programs(self, limit: int = 50) -> list[SemanticProgram]:
        """List semantic programs ordered newest-first."""
        ...

    @abstractmethod
    def write_execution(self, execution: ProgramExecution) -> None:
        """Persist a semantic program execution."""
        ...

    @abstractmethod
    def read_execution(self, execution_id: str) -> ProgramExecution:
        """Read a semantic program execution by id."""
        ...

    @abstractmethod
    def query_executions(self, program_id: str, limit: int = 50) -> list[ProgramExecution]:
        """List executions for a program ordered newest-first."""
        ...

    @abstractmethod
    def write_emergent_aspect(self, aspect: EmergentAspect) -> None:
        """Persist an emergent aspect proposal."""
        ...

    @abstractmethod
    def read_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        """Read an emergent aspect proposal by id."""
        ...

    @abstractmethod
    def query_emergent_aspects(
        self, status: str | None = None, limit: int = 50
    ) -> list[EmergentAspect]:
        """List emergent aspect proposals, optionally filtered by status."""
        ...

    @abstractmethod
    def accept_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        """Mark a proposal accepted and register it as a concrete aspect."""
        ...

    @abstractmethod
    def reject_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        """Mark an emergent aspect proposal as rejected."""
        ...

    @abstractmethod
    def write_causal_edge(self, edge: CausalEdge) -> None:
        """Persist a typed causal edge."""
        ...

    @abstractmethod
    def read_causal_edge(self, edge_id: str) -> CausalEdge:
        """Read a causal edge by id."""
        ...

    @abstractmethod
    def query_causal_edges(
        self,
        cast_id: str | None = None,
        edge_types: list[str] | None = None,
        min_weight: float = 0.0,
        limit: int = 100,
    ) -> list[CausalEdge]:
        """List causal edges with optional endpoint and type filters."""
        ...

    @abstractmethod
    def causal_subgraph(self, query: CausalQuery) -> CausalSubgraph:
        """Traverse the causal graph and return a filtered subgraph."""
        ...

    @abstractmethod
    def delete_causal_edge(self, edge_id: str) -> None:
        """Delete a causal edge by id."""
        ...

    @abstractmethod
    def write_policy_decision(self, decision: PolicyDecision) -> None:
        """Persist a policy decision."""
        ...

    @abstractmethod
    def read_policy_decision(self, decision_id: str) -> PolicyDecision:
        """Read a policy decision by id."""
        ...

    @abstractmethod
    def query_policy_decisions(
        self,
        action: PolicyAction | None = None,
        *,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[PolicyDecision]:
        """List policy decisions newest-first."""
        ...

    @abstractmethod
    def delete(self, cast_id: str) -> None:
        """Remove a CastResult from the grimoire by cast_id.

        Raises KeyError if cast_id is not found. Raises RuntimeError if the
        underlying store is unavailable.
        """
        ...


# -----------------------------------------------------------------------------
# Section 3: MCP Server
# -----------------------------------------------------------------------------


class MCPServerContract(ABC):
    """Abstract contract for MCP tool entry points."""

    @abstractmethod
    def tool_decide(
        self,
        *,
        intent: dict,
        aspects: list[str] | None = None,
        vector: list[float] | None = None,
        parent_cast_id: str | None = None,
        causal_root_cast_id: str | None = None,
        thresholds: dict | None = None,
    ) -> dict:
        """MCP tool entry point for policy decision gating."""
        ...

    @abstractmethod
    def tool_cast(self, aspects: list[str], intent: dict) -> dict:
        """MCP tool entry point for casting.

        Accepts aspects as a list of AspectID name strings and intent as a raw
        dict matching the Intent schema. Deserializes inputs into schema types,
        delegates to EngineContract.cast, persists result via
        GrimoireContract.write, and returns the CastResult serialized as a dict.
        Raises ValueError if any aspect name is not a valid AspectID. Raises
        ValueError if intent dict fails Intent validation.
        """
        ...

    @abstractmethod
    def tool_query(self, filters: dict) -> list[dict]:
        """MCP tool entry point for field-based grimoire queries.

        Accepts filters as a raw dict matching the SemanticQuery schema.
        Deserializes into SemanticQuery, delegates to GrimoireContract.query,
        returns list of CastResults serialized as dicts. Raises ValueError if
        filters dict fails SemanticQuery validation.
        """
        ...

    @abstractmethod
    def tool_semantic_search(
        self, proximity_vector: list[float], threshold: float, limit: int
    ) -> list[dict]:
        """MCP tool entry point for semantic proximity search.

        Accepts a six-element float list as the query vector, a similarity
        threshold, and a result limit. Constructs a SemanticVector and
        SemanticQuery, delegates to GrimoireContract.semantic_search, returns
        list of CastResults serialized as dicts. Raises ValueError if
        proximity_vector does not have exactly six elements. Raises ValueError
        if threshold is outside 0.0 to 1.0.
        """
        ...

    @abstractmethod
    def tool_inspect(self, cast_id: str) -> dict:
        """MCP tool entry point for retrieving a single CastResult by cast_id.

        Delegates to GrimoireContract.read. Returns CastResult serialized as
        dict. Raises KeyError if cast_id not found.
        """
        ...

    @abstractmethod
    def tool_seeds(self, crystallized: Optional[bool]) -> list[dict]:
        """MCP tool entry point for querying GlyphSeeds.

        Returns all seeds optionally filtered by crystallized status. Delegates
        to GrimoireContract.query_seeds. Returns list of GlyphSeeds serialized
        as dicts.
        """
        ...

    @abstractmethod
    def tool_crystallized_sigils(self) -> list[dict]:
        """MCP tool entry point for listing crystallized Sigils."""
        ...

    @abstractmethod
    def tool_register_aspect(self, aspect_id: str, polarity: int, entropy_coefficient: float, symbol: str) -> dict:
        """MCP tool entry point for registering a new Aspect."""
        ...

    @abstractmethod
    def tool_register_sigil(self, payload: dict) -> dict:
        """MCP tool entry point for registering a named Sigil override."""
        ...

    @abstractmethod
    def tool_registered_aspects(self) -> list[dict]:
        """MCP tool entry point for listing registered Aspects."""
        ...

    @abstractmethod
    def tool_registered_sigils(self) -> list[dict]:
        """MCP tool entry point for listing registered Sigils."""
        ...

    @abstractmethod
    def tool_divergence(self, cast_id: str) -> dict:
        """MCP tool entry point for reading a divergence report."""
        ...

    @abstractmethod
    def tool_set_divergence_thresholds(self, payload: dict) -> dict:
        """MCP tool entry point for updating divergence thresholds."""
        ...

    @abstractmethod
    def tool_divergence_thresholds(self) -> dict:
        """MCP tool entry point for reading divergence thresholds."""
        ...


# -----------------------------------------------------------------------------
# Section 4: CLI
# -----------------------------------------------------------------------------


class CLIContract(ABC):
    """Abstract contract for CLI command handlers."""

    @abstractmethod
    def cmd_decide(
        self,
        *,
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
        aspects: list[str] | None = None,
        vector: list[float] | None = None,
        parent_cast_id: str | None = None,
        causal_root_cast_id: str | None = None,
    ) -> None:
        """CLI command for policy decision gating."""
        ...

    @abstractmethod
    def cmd_cast(
        self,
        aspects: list[str],
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
        *,
        parent_cast_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> None:
        """CLI command for casting.

        Accepts all inputs as strings, deserializes into schema types, delegates
        to EngineContract.cast, persists via GrimoireContract.write, prints a
        human readable cast result summary to stdout. Prints error message to
        stderr and exits with code 1 on validation failure.
        """
        ...

    @abstractmethod
    def cmd_query(
        self,
        verdict: Optional[str],
        min_resonance: Optional[float],
        branch_id: Optional[str],
        limit: int,
    ) -> None:
        """CLI command for field-based grimoire query.

        Constructs a SemanticQuery from arguments, delegates to
        GrimoireContract.query, prints results as a formatted table to stdout.
        Prints empty state message if no results. Prints error to stderr and
        exits with code 1 on validation failure.
        """
        ...

    @abstractmethod
    def cmd_search(self, vector: list[float], threshold: float, limit: int) -> None:
        """CLI command for semantic proximity search.

        Constructs SemanticVector and SemanticQuery, delegates to
        GrimoireContract.semantic_search, prints results ordered by similarity to
        stdout. Prints error to stderr and exits with code 1 on validation
        failure.
        """
        ...

    @abstractmethod
    def cmd_inspect(self, cast_id: str) -> None:
        """CLI command for inspecting a single CastResult.

        Delegates to GrimoireContract.read, prints full cast result detail to
        stdout including lineage chain if present. Prints error to stderr and
        exits with code 1 if cast_id not found.
        """
        ...

    @abstractmethod
    def cmd_seeds(self, crystallized: Optional[bool]) -> None:
        """CLI command for inspecting GlyphSeeds.

        Delegates to GrimoireContract.query_seeds, prints seed summary table to
        stdout including observed_count, mean_resonance, coherence_rate, and
        crystallized status. Prints empty state message if no seeds.
        """
        ...

    @abstractmethod
    def cmd_crystallized_sigils(self) -> None:
        """CLI command for listing crystallized Sigils."""
        ...

    @abstractmethod
    def cmd_register_aspect(
        self, aspect_id: str, polarity: int, entropy_coefficient: float, symbol: str
    ) -> None:
        """CLI command for registering a new Aspect."""
        ...

    @abstractmethod
    def cmd_register_sigil(self, payload: dict) -> None:
        """CLI command for registering a named Sigil override."""
        ...

    @abstractmethod
    def cmd_aspects(self) -> None:
        """CLI command for listing all aspects (canonical + registered)."""
        ...

    @abstractmethod
    def cmd_registered_sigils(self) -> None:
        """CLI command for listing registered Sigils."""
        ...

    @abstractmethod
    def cmd_divergence(self, cast_id: str) -> None:
        """CLI command for printing a divergence report by cast_id."""
        ...

    @abstractmethod
    def cmd_set_thresholds(
        self,
        l2_stable: Optional[float],
        l2_diverged: Optional[float],
        cosine_stable: Optional[float],
        cosine_diverged: Optional[float],
    ) -> None:
        """CLI command for updating divergence thresholds."""
        ...

    @abstractmethod
    def cmd_thresholds(self) -> None:
        """CLI command for printing active divergence thresholds."""
        ...


# -----------------------------------------------------------------------------
# Section 5: Extension API
# -----------------------------------------------------------------------------


class ExtensionContract(ABC):
    """Abstract contract for extending aspects and named sigils."""

    @abstractmethod
    def register_aspect(
        self,
        aspect_id: str,
        polarity: int,
        entropy_coefficient: float,
        symbol: str,
    ) -> None:
        """Register a new Aspect beyond the six canonical members.

        The aspect_id must be a unique string not matching any existing AspectID
        name. polarity must be -1 or 1. entropy_coefficient must be in 0.0 to
        1.0. symbol must be a single unicode character. Raises ValueError on any
        constraint violation. Raises ValueError if aspect_id already exists.
        Note: extended aspects expand the SemanticVector dimensionality — all
        existing vectors must be padded with 0.0 for the new dimension. This
        operation is append-only and irreversible within a session.
        """
        ...

    @abstractmethod
    def register_sigil(
        self,
        name: str,
        aspects: frozenset[Aspect],
        effect_class: EffectClass,
        resonance_ceiling: float,
        contradiction_severity: ContradictionSeverity,
        *,
        allow_override: bool = False,
    ) -> Sigil:
        """Register a named Sigil for a specific aspect combination.

        Overrides or extends the default composition table. Raises ValueError if
        a sigil for this exact aspect combination already exists and override is
        not explicitly permitted. Returns the registered Sigil.
        """
        ...


# -----------------------------------------------------------------------------
# Section 6: Projection Backend
# -----------------------------------------------------------------------------


class ProjectionBackend(ABC):
    """Abstract contract for projecting intent text into aspect space."""

    @abstractmethod
    def project(self, objective: str, scope: str) -> list[float]:
        """Project an intent's objective and scope into aspect space.

        Returns a list of floats in canonical aspect order: VOID, FORM, MOTION,
        MIND, DECAY, LIGHT, optionally followed by additional dimensions for any
        registered aspects. The list must contain at least 6 floats; additional
        dimensions should be aligned to the session's AspectRegistry order.

        Each float must be in range -1.0 to 1.0. Positive values indicate
        alignment with that aspect. Negative values indicate opposition. Zero
        indicates neutrality.

        Raises NotImplementedError if not implemented by subclass. Raises
        RuntimeError if the backend is unavailable. Raises ValueError if the
        returned list is invalid (wrong shape or values).
        """
        ...
