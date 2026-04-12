from abc import ABC, abstractmethod
from typing import Optional

from vermyth.schema import (
    AspectID,
    CastResult,
    ContradictionSeverity,
    EffectClass,
    GlyphSeed,
    Intent,
    SemanticQuery,
    Sigil,
    Verdict,
)

# -----------------------------------------------------------------------------
# Section 1: Engine
# -----------------------------------------------------------------------------


class EngineContract(ABC):
    """Abstract contract for the Vermyth execution engine."""

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
        aspect_pattern: Optional[frozenset[AspectID]],
        crystallized: Optional[bool],
    ) -> list[GlyphSeed]:
        """Retrieve GlyphSeeds filtered by aspect pattern and crystallized flag.

        Returns all seeds if both filters are None. Returns empty list if no
        seeds match.
        """
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


# -----------------------------------------------------------------------------
# Section 4: CLI
# -----------------------------------------------------------------------------


class CLIContract(ABC):
    """Abstract contract for CLI command handlers."""

    @abstractmethod
    def cmd_cast(
        self,
        aspects: list[str],
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
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
        aspects: frozenset[AspectID],
        effect_class: EffectClass,
        resonance_ceiling: float,
        contradiction_severity: ContradictionSeverity,
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
        """Project an intent's objective and scope into six-dimensional aspect space.

        Returns exactly six floats in canonical aspect order: VOID, FORM, MOTION,
        MIND, DECAY, LIGHT. Each float must be in range -1.0 to 1.0. Positive
        values indicate alignment with that aspect. Negative values indicate
        opposition. Zero indicates neutrality. Raises NotImplementedError if not
        implemented by subclass. Raises RuntimeError if the backend is
        unavailable. Raises ValueError if the returned list does not contain
        exactly six floats each in range -1.0 to 1.0.
        """
        ...
