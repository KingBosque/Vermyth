"""SQLite-backed grimoire: CastResult and GlyphSeed persistence."""

from __future__ import annotations

import json
import sqlite3
import heapq
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from vermyth.contracts import GrimoireContract
from vermyth.engine.keys import canonical_aspect_key
from vermyth.grimoire.repositories.basis_versions import BasisVersionRepository
from vermyth.grimoire.repositories.casts import CastRepository
from vermyth.grimoire.repositories.causal import CausalRepository
from vermyth.grimoire.repositories.channels import ChannelRepository
from vermyth.grimoire.repositories.crystallized import CrystallizedRepository
from vermyth.grimoire.repositories.decisions import DecisionRepository
from vermyth.grimoire.repositories.divergence import DivergenceRepository
from vermyth.grimoire.repositories.genesis import GenesisRepository
from vermyth.grimoire.repositories.programs import ProgramRepository
from vermyth.grimoire.repositories.registry import RegistryRepository
from vermyth.grimoire.repositories.seeds import SeedRepository
from vermyth.grimoire.repositories.sessions import SessionRepository
from vermyth.grimoire.repositories.swarm import SwarmRepository
from vermyth.registry import AspectRegistry
from vermyth.schema import (
    Aspect,
    BasisVersion,
    RegisteredAspect,
    CastResult,
    CastProvenance,
    CausalEdge,
    CausalEdgeType,
    CausalQuery,
    CausalSubgraph,
    CanonicalPacketV2,
    CanonicalResponseV2,
    ChannelState,
    ChannelStatus,
    ContradictionSeverity,
    CrystallizedSigil,
    DivergenceReport,
    DivergenceStatus,
    DivergenceThresholds,
    DivergenceThresholds_DEFAULT,
    EmergentAspect,
    EffectClass,
    GenesisStatus,
    GossipPayload,
    GlyphSeed,
    Intent,
    IntentVector,
    Lineage,
    Polarity,
    PolicyAction,
    PolicyDecision,
    PolicyThresholds,
    ProjectionMethod,
    ProgramExecution,
    ProgramStatus,
    ResonanceScore,
    SemanticProgram,
    SemanticQuery,
    SemanticVector,
    SessionRecord,
    SessionStatus,
    SessionTransport,
    Sigil,
    SwarmState,
    SwarmStatus,
    Verdict,
    VerdictType,
    current_basis_version,
)
class Grimoire(GrimoireContract):
    """Persistent cast and seed storage using SQLite."""
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self._path = Path.home() / ".vermyth" / "grimoire.db"
        else:
            self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self.casts = CastRepository(self._conn)
        self.seeds = SeedRepository(self._conn)
        self.crystallized = CrystallizedRepository(self._conn)
        self.divergence = DivergenceRepository(self._conn)
        self.channels = ChannelRepository(self._conn)
        self.sessions = SessionRepository(self._conn)
        self.basis_versions = BasisVersionRepository(self._conn)
        self.registry = RegistryRepository(self._conn)
        self.genesis = GenesisRepository(self._conn, self.registry)
        self.causal = CausalRepository(self._conn)
        self.swarm = SwarmRepository(self._conn)
        self.programs = ProgramRepository(self._conn)
        self.decisions = DecisionRepository(self._conn)
        self._run_migrations()
    def _run_migrations(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        has_migrations = cur.fetchone() is not None
        applied: set[str] = set()
        if has_migrations:
            cur.execute("SELECT version FROM schema_migrations")
            applied = {r["version"] for r in cur.fetchall()}

        migrations = [
            ("v001", "v001_initial.sql"),
            ("v002", "v002_crystallized_loop.sql"),
            ("v003", "v003_extension_api.sql"),
            ("v004", "v004_divergence_detection.sql"),
            ("v005", "v005_observability_indexes.sql"),
            ("v006", "v006_cast_aspect_pattern_key.sql"),
            ("v007", "v007_channel_states.sql"),
            ("v008", "v008_sessions.sql"),
            ("v009", "v009_swarm_federation.sql"),
            ("v010", "v010_semantic_programs.sql"),
            ("v011", "v011_emergent_aspects.sql"),
            ("v012", "v012_causal_graph.sql"),
            ("v013", "v013_basis_versions.sql"),
            ("v014", "v014_policy_decisions.sql"),
            ("v015", "v015_cast_provenance_extend.sql"),
            ("v016", "v016_policy_decision_model.sql"),
        ]
        for version, filename in migrations:
            if version in applied:
                continue
            sql_path = Path(__file__).parent / "migrations" / filename
            self._conn.executescript(sql_path.read_text(encoding="utf-8"))
            cur.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(timezone.utc).isoformat()),
            )
            self._conn.commit()
        self._backfill_cast_aspect_pattern_keys()
        latest_basis = self.read_latest_basis_version()
        AspectRegistry.get().set_basis_version(latest_basis.version)
    def _backfill_cast_aspect_pattern_keys(self) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT cast_id, sigil_json FROM cast_results WHERE aspect_pattern_key IS NULL"
            )
            rows = cur.fetchall()
            if not rows:
                return
            updates: list[tuple[str, str]] = []
            for row in rows:
                sigil_d = json.loads(row["sigil_json"])
                aspects = frozenset(
                    AspectRegistry.get().resolve(n) for n in sigil_d["aspects"]
                )
                updates.append((canonical_aspect_key(aspects), row["cast_id"]))
            cur.executemany(
                "UPDATE cast_results SET aspect_pattern_key = ? WHERE cast_id = ?",
                updates,
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
    def write_basis_version(self, basis: BasisVersion) -> None:
        self.basis_versions.write_basis_version(basis)
    def read_basis_version(self, version: int) -> BasisVersion:
        return self.basis_versions.read_basis_version(version)
    def read_latest_basis_version(self) -> BasisVersion:
        return self.basis_versions.read_latest_basis_version()
    def write(self, result: CastResult) -> None:
        self.casts.write(result)
    def read(self, cast_id: str) -> CastResult:
        return self.casts.read(cast_id)
    def query(self, query: SemanticQuery) -> list[CastResult]:
        return self.casts.query(query)
    def semantic_search(self, query: SemanticQuery) -> list[CastResult]:
        return self.casts.semantic_search(query)
    def write_seed(self, seed: GlyphSeed) -> None:
        self.seeds.write_seed(seed)
    def write_crystallized_sigil(self, crystal: CrystallizedSigil) -> None:
        self.crystallized.write_crystallized_sigil(crystal)
    def read_crystallized_sigil(self, name: str) -> CrystallizedSigil:
        return self.crystallized.read_crystallized_sigil(name)
    def crystallized_for_aspects(
        self, aspects: frozenset[Aspect]
    ) -> CrystallizedSigil | None:
        return self.crystallized.crystallized_for_aspects(aspects)
    def query_crystallized_sigils(self) -> list[CrystallizedSigil]:
        return self.crystallized.query_crystallized_sigils()
    def read_seed(self, seed_id: str) -> GlyphSeed:
        return self.seeds.read_seed(seed_id)
    def query_seeds(
        self,
        aspect_pattern: Optional[frozenset[Aspect]],
        crystallized: Optional[bool],
    ) -> list[GlyphSeed]:
        return self.seeds.query_seeds(aspect_pattern=aspect_pattern, crystallized=crystallized)
    def write_registered_aspect(self, aspect: RegisteredAspect, ordinal: int) -> None:
        self.registry.write_registered_aspect(aspect, ordinal)
    def query_registered_aspects(self) -> list[tuple[RegisteredAspect, int]]:
        return self.registry.query_registered_aspects()
    def write_registered_sigil(
        self,
        name: str,
        aspects: list[str],
        effect_class: str,
        resonance_ceiling: float,
        contradiction_severity: str,
        is_override: bool,
    ) -> None:
        self.registry.write_registered_sigil(
            name=name,
            aspects=aspects,
            effect_class=effect_class,
            resonance_ceiling=resonance_ceiling,
            contradiction_severity=contradiction_severity,
            is_override=is_override,
        )
    def read_registered_sigil(self, name: str) -> dict:
        return self.registry.read_registered_sigil(name)
    def query_registered_sigils(self) -> list[dict]:
        return self.registry.query_registered_sigils()
    def write_divergence_report(self, report: DivergenceReport) -> None:
        self.divergence.write_divergence_report(report)
    def read_divergence_report(self, cast_id: str) -> DivergenceReport:
        return self.divergence.read_divergence_report(cast_id)
    def query_divergence_reports(
        self,
        status: DivergenceStatus | None = None,
        limit: int = 50,
        *,
        since: datetime | None = None,
    ) -> list[DivergenceReport]:
        return self.divergence.query_divergence_reports(
            status=status,
            limit=limit,
            since=since,
        )
    def write_divergence_thresholds(self, thresholds: DivergenceThresholds) -> None:
        self.divergence.write_divergence_thresholds(thresholds)
    def read_divergence_thresholds(self) -> DivergenceThresholds:
        return self.divergence.read_divergence_thresholds()
    def drift_branches(self, limit: int = 25) -> list[dict[str, Any]]:
        return self.divergence.drift_branches(limit=limit)
    def cast_pairs_missing_divergence_reports(self, limit: int = 500) -> list[tuple[str, str]]:
        return self.divergence.cast_pairs_missing_divergence_reports(limit=limit)
    def write_channel_state(self, state: ChannelState) -> None:
        self.channels.write_channel_state(state)
    def read_channel_state(self, branch_id: str) -> ChannelState:
        return self.channels.read_channel_state(branch_id)
    def query_channel_states(self, status: Optional[str], limit: int) -> list[ChannelState]:
        return self.channels.query_channel_states(status=status, limit=limit)
    def write_session(self, session: SessionRecord) -> None:
        self.sessions.write_session(session)
    def read_session(self, session_id: str) -> SessionRecord:
        return self.sessions.read_session(session_id)
    def close_session(self, session_id: str) -> SessionRecord:
        return self.sessions.close_session(session_id)
    def advance_session_sequence(self, session_id: str, new_sequence: int) -> SessionRecord:
        return self.sessions.advance_session_sequence(session_id, new_sequence)
    def write_session_packet(self, packet: CanonicalPacketV2) -> None:
        self.sessions.write_session_packet(packet)
    def write_session_response(self, response: CanonicalResponseV2) -> None:
        self.sessions.write_session_response(response)
    def query_session_packets(self, session_id: str, limit: int) -> list[CanonicalPacketV2]:
        return self.sessions.query_session_packets(session_id, limit)
    def query_session_responses(self, session_id: str, limit: int) -> list[CanonicalResponseV2]:
        return self.sessions.query_session_responses(session_id, limit)
    def write_swarm_state(self, state: SwarmState) -> None:
        self.swarm.write_swarm_state(state)
    def read_swarm_state(self, swarm_id: str) -> SwarmState:
        return self.swarm.read_swarm_state(swarm_id)
    def upsert_swarm_member(
        self,
        swarm_id: str,
        session_id: str,
        vector: SemanticVector,
        coherence_streak: int,
    ) -> None:
        self.swarm.upsert_swarm_member(
            swarm_id=swarm_id,
            session_id=session_id,
            vector=vector,
            coherence_streak=coherence_streak,
        )
    def query_swarm_members(self, swarm_id: str) -> list[tuple[str, SemanticVector, int]]:
        return self.swarm.query_swarm_members(swarm_id)
    def write_program(self, program: SemanticProgram) -> None:
        self.programs.write_program(program)
    def read_program(self, program_id: str) -> SemanticProgram:
        return self.programs.read_program(program_id)
    def query_programs(self, limit: int = 50) -> list[SemanticProgram]:
        return self.programs.query_programs(limit=limit)
    def write_execution(self, execution: ProgramExecution) -> None:
        self.programs.write_execution(execution)
    def read_execution(self, execution_id: str) -> ProgramExecution:
        return self.programs.read_execution(execution_id)
    def query_executions(self, program_id: str, limit: int = 50) -> list[ProgramExecution]:
        return self.programs.query_executions(program_id=program_id, limit=limit)
    def write_emergent_aspect(self, aspect: EmergentAspect) -> None:
        self.genesis.write_emergent_aspect(aspect)
    def read_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        return self.genesis.read_emergent_aspect(genesis_id)
    def query_emergent_aspects(
        self, status: str | None = None, limit: int = 50
    ) -> list[EmergentAspect]:
        return self.genesis.query_emergent_aspects(status=status, limit=limit)
    def accept_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        return self.genesis.accept_emergent_aspect(genesis_id)
    def reject_emergent_aspect(self, genesis_id: str) -> EmergentAspect:
        return self.genesis.reject_emergent_aspect(genesis_id)
    def write_causal_edge(self, edge: CausalEdge) -> None:
        self.causal.write_causal_edge(edge)
    def read_causal_edge(self, edge_id: str) -> CausalEdge:
        return self.causal.read_causal_edge(edge_id)
    def query_causal_edges(
        self,
        cast_id: str | None = None,
        edge_types: list[str] | None = None,
        min_weight: float = 0.0,
        limit: int = 100,
    ) -> list[CausalEdge]:
        return self.causal.query_causal_edges(
            cast_id=cast_id,
            edge_types=edge_types,
            min_weight=min_weight,
            limit=limit,
        )
    def causal_subgraph(self, query: CausalQuery) -> CausalSubgraph:
        return self.causal.causal_subgraph(query)
    def delete_causal_edge(self, edge_id: str) -> None:
        self.causal.delete_causal_edge(edge_id)
    def apply_gossip_sync(self, payload: GossipPayload) -> dict[str, Any]:
        return self.swarm.apply_gossip_sync(payload, self)
    def write_policy_decision(self, decision: PolicyDecision) -> None:
        self.decisions.write_policy_decision(decision)
    def read_policy_decision(self, decision_id: str) -> PolicyDecision:
        return self.decisions.read_policy_decision(decision_id)
    def query_policy_decisions(
        self,
        action: PolicyAction | None = None,
        *,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[PolicyDecision]:
        return self.decisions.query_policy_decisions(
            action=action,
            since=since,
            limit=limit,
        )
    def delete(self, cast_id: str) -> None:
        self.casts.delete(cast_id)
    def close(self) -> None:
        """Close the underlying SQLite connection. Call when the Grimoire is no longer needed."""
        self._conn.close()
