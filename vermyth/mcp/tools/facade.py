"""MCP tool handlers: Vermyth engine and grimoire wiring (no JSON-RPC protocol)."""

from __future__ import annotations

import fnmatch
from datetime import datetime, timezone
from typing import Any, Optional

from ulid import ULID

from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.registry import AspectRegistry
from vermyth.protocol.session_codec import (
    SessionKeys,
    encode_packet as encode_session_packet,
    encode_response as encode_session_response,
    verify_packet_proof,
)
from vermyth.schema import (
    CanonicalPacketV2,
    CanonicalResponseV2,
    CastResult,
    CastProvenance,
    CausalEdge,
    CausalEdgeType,
    CausalQuery,
    ChannelState,
    ChannelStatus,
    ContradictionSeverity,
    CrystallizedSigil,
    DivergenceReport,
    DivergenceStatus,
    DivergenceThresholds,
    DivergenceThresholds_DEFAULT,
    EffectClass,
    EmergentAspect,
    GossipPayload,
    GlyphSeed,
    Intent,
    Lineage,
    NegotiatedCapabilities,
    PeerIdentity,
    ProgramExecution,
    RegisteredAspect,
    CausalSubgraph,
    PolicyDecision,
    PolicyThresholds,
    SemanticProgram,
    SemanticQuery,
    SemanticVector,
    SessionRecord,
    SessionStatus,
    SessionTransport,
    Sigil,
    SwarmState,
    SwarmStatus,
    VerdictType,
)
from vermyth.mcp.geometric import decode_packet, encode_response, validate_proof
from vermyth.observability import EventBus
from vermyth.mcp.tools import arcane as arcane_tools
from vermyth.mcp.tools import casting as casting_tools
from vermyth.mcp.tools import causal as causal_tools
from vermyth.mcp.tools import decisions as decision_tools
from vermyth.mcp.tools import drift as drift_tools
from vermyth.mcp.tools import genesis as genesis_tools
from vermyth.mcp.tools import programs as program_tools
from vermyth.mcp.tools import query as query_tools
from vermyth.mcp.tools import registry as registry_tools
from vermyth.mcp.tools import seeds as seed_tools
from vermyth.mcp.tools import session as session_tools
from vermyth.mcp.tools import swarm as swarm_tools
from vermyth.mcp.tools._serializers import policy_decision_to_dict
from vermyth.schema import GeometricPacket


class PermissionDenied(RuntimeError):
    pass


class VermythTools:
    """Execute MCP tools against a ResonanceEngine and Grimoire."""
    def __init__(
        self,
        engine: ResonanceEngine,
        grimoire: Grimoire,
        *,
        event_bus: EventBus | None = None,
        allowed_tool_scope: list[str] | None = None,
    ) -> None:
        self._engine = engine
        self._grimoire = grimoire
        self._event_bus = event_bus or EventBus()
        self._active_thresholds: DivergenceThresholds = (
            grimoire.read_divergence_thresholds()
            if hasattr(grimoire, "read_divergence_thresholds")
            else DivergenceThresholds_DEFAULT
        )
        self._divergence_cache: dict[str, DivergenceReport] = {}
        self._allowed_tool_scope = list(allowed_tool_scope or ["*"])

    def enforce_tool_scope(self, tool_name: str) -> None:
        if any(fnmatch.fnmatch(tool_name, pat) for pat in self._allowed_tool_scope):
            return
        raise PermissionDenied(f"tool_scope_denied:{tool_name}")
    def _emit_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        cast_id: str | None = None,
        branch_id: str | None = None,
    ) -> None:
        self._event_bus.emit_event(
            event_type=event_type,
            payload=payload,
            cast_id=cast_id,
            branch_id=branch_id,
        )
    def tool_events_tail(
        self, *, n: int = 100, event_type: str | None = None
    ) -> list[dict[str, Any]]:
        return [ev.to_dict() for ev in self._event_bus.recent(n, event_type=event_type)]
    def _cast_result_to_dict(self, result: CastResult) -> dict[str, Any]:
        return casting_tools.cast_result_to_dict(self, result)
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
            "generation": int(getattr(seed, "generation", 1) or 1),
            "semantic_vector": [
                round(c, 6) for c in seed.semantic_vector.components
            ],
        }
    def _crystallized_sigil_to_dict(self, crystal: CrystallizedSigil) -> dict[str, Any]:
        return {
            "name": crystal.name,
            "generation": int(crystal.generation),
            "crystallized_at": crystal.crystallized_at.isoformat(),
            "source_seed_id": crystal.source_seed_id,
            "sigil": {
                "name": crystal.sigil.name,
                "aspects": sorted([a.name for a in crystal.sigil.aspects]),
                "effect_class": crystal.sigil.effect_class.name,
                "resonance_ceiling": crystal.sigil.resonance_ceiling,
                "contradiction_severity": crystal.sigil.contradiction_severity.name,
                "semantic_vector": [
                    round(c, 6) for c in crystal.sigil.semantic_vector.components
                ],
            },
        }
    def _channel_state_to_dict(self, state: ChannelState) -> dict[str, Any]:
        return {
            "branch_id": state.branch_id,
            "cast_count": int(state.cast_count),
            "cumulative_resonance": round(float(state.cumulative_resonance), 6),
            "mean_resonance": round(float(state.mean_resonance), 6),
            "coherence_streak": int(state.coherence_streak),
            "last_verdict_type": state.last_verdict_type.name,
            "status": state.status.name,
            "last_cast_id": state.last_cast_id,
            "constraint_vector": (
                [round(c, 6) for c in state.constraint_vector.components]
                if state.constraint_vector is not None
                else None
            ),
            "updated_at": state.updated_at.isoformat(),
        }
    def _program_to_dict(self, program: SemanticProgram) -> dict[str, Any]:
        return program_tools.program_to_dict(program)
    def _execution_to_dict(self, execution: ProgramExecution) -> dict[str, Any]:
        return program_tools.execution_to_dict(execution)
    def _emergent_aspect_to_dict(self, aspect: EmergentAspect) -> dict[str, Any]:
        return genesis_tools.emergent_aspect_to_dict(aspect)
    def _causal_edge_to_dict(self, edge: CausalEdge) -> dict[str, Any]:
        return causal_tools.causal_edge_to_dict(edge)
    def _causal_subgraph_to_dict(self, graph: CausalSubgraph) -> dict[str, Any]:
        return causal_tools.causal_subgraph_to_dict(graph)
    def _policy_decision_to_dict(self, decision: PolicyDecision) -> dict[str, Any]:
        return policy_decision_to_dict(decision)
    def tool_compile_program(self, payload: dict[str, Any]) -> dict[str, Any]:
        return program_tools.tool_compile_program(self, payload)
    def tool_execute_program(self, program_id: str) -> dict[str, Any]:
        out = program_tools.tool_execute_program(self, program_id)
        self._emit_event(
            "program_execute",
            {"program_id": program_id, "execution_id": out.get("execution_id")},
        )
        return out
    def tool_program_status(self, program_id: str) -> dict[str, Any]:
        return program_tools.tool_program_status(self, program_id)
    def tool_list_programs(self, limit: int = 50) -> list[dict[str, Any]]:
        return program_tools.tool_list_programs(self, limit)
    def tool_execution_status(self, execution_id: str) -> dict[str, Any]:
        return program_tools.tool_execution_status(self, execution_id)
    def tool_execution_receipt(self, execution_id: str) -> dict[str, Any]:
        return program_tools.tool_execution_receipt(self, execution_id)
    def tool_verify_execution_receipt(
        self, receipt: dict[str, Any], *, public_pem: str | None = None
    ) -> dict[str, Any]:
        return program_tools.tool_verify_execution_receipt(self, receipt, public_pem=public_pem)
    def tool_expand_semantic_bundle(self, skill_id: str, input: dict[str, Any]) -> dict[str, Any]:
        return arcane_tools.tool_expand_semantic_bundle(self, skill_id=skill_id, input=input)
    def tool_compile_ritual(self, ritual: dict[str, Any]) -> dict[str, Any]:
        return arcane_tools.tool_compile_ritual(self, ritual=ritual)
    def tool_list_semantic_bundles(self, kind: str | None = None) -> dict[str, Any]:
        return arcane_tools.tool_list_semantic_bundles(self, kind=kind)
    def tool_inspect_semantic_bundle(
        self,
        bundle_id: str,
        version: int,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return arcane_tools.tool_inspect_semantic_bundle(
            self, bundle_id=bundle_id, version=version, params=params
        )
    def tool_recommend_semantic_bundles(
        self,
        skill_id: str,
        input: dict[str, Any],
        min_strength: float | None = None,
    ) -> dict[str, Any]:
        return arcane_tools.tool_recommend_semantic_bundles(
            self, skill_id=skill_id, input=input, min_strength=min_strength
        )
    def tool_get_bundle_adoption_telemetry(self) -> dict[str, Any]:
        return arcane_tools.tool_get_bundle_adoption_telemetry(self)
    def tool_get_bundle_adoption_report(self) -> dict[str, Any]:
        return arcane_tools.tool_get_bundle_adoption_report(self)
    def tool_propose_genesis(
        self,
        *,
        history_limit: int = 500,
        min_cluster_size: int = 15,
        min_unexplained_variance: float = 0.3,
        min_coherence_rate: float = 0.6,
    ) -> list[dict[str, Any]]:
        out = genesis_tools.tool_propose_genesis(
            self,
            history_limit=history_limit,
            min_cluster_size=min_cluster_size,
            min_unexplained_variance=min_unexplained_variance,
            min_coherence_rate=min_coherence_rate,
        )
        self._emit_event("genesis_propose", {"count": len(out)})
        return out
    def tool_genesis_proposals(
        self, *, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        return genesis_tools.tool_genesis_proposals(self, status=status, limit=limit)
    def tool_accept_genesis(self, genesis_id: str) -> dict[str, Any]:
        return genesis_tools.tool_accept_genesis(self, genesis_id)
    def tool_reject_genesis(self, genesis_id: str) -> dict[str, Any]:
        return genesis_tools.tool_reject_genesis(self, genesis_id)
    def tool_review_genesis(self, genesis_id: str, reviewer: str, note: str | None = None) -> dict[str, Any]:
        return genesis_tools.tool_review_genesis(
            self,
            genesis_id=genesis_id,
            reviewer=reviewer,
            note=note,
        )
    def tool_infer_causal_edge(self, source_cast_id: str, target_cast_id: str) -> dict[str, Any]:
        out = causal_tools.tool_infer_causal_edge(self, source_cast_id, target_cast_id)
        self._emit_event(
            "causal_infer",
            {"source_cast_id": source_cast_id, "target_cast_id": target_cast_id},
        )
        return out
    def tool_add_causal_edge(self, payload: dict[str, Any]) -> dict[str, Any]:
        return causal_tools.tool_add_causal_edge(self, payload)
    def tool_causal_subgraph(
        self,
        *,
        root_cast_id: str,
        edge_types: list[str] | None = None,
        direction: str = "both",
        max_depth: int = 5,
        min_weight: float = 0.0,
    ) -> dict[str, Any]:
        return causal_tools.tool_causal_subgraph(
            self,
            root_cast_id=root_cast_id,
            edge_types=edge_types,
            direction=direction,
            max_depth=max_depth,
            min_weight=min_weight,
        )
    def tool_evaluate_narrative(self, edge_ids: list[str]) -> dict[str, Any]:
        return causal_tools.tool_evaluate_narrative(self, edge_ids)
    def tool_predictive_cast(self, root_cast_id: str, intent: dict[str, Any]) -> dict[str, Any]:
        return causal_tools.tool_predictive_cast(self, root_cast_id, intent)
    def tool_decide(
        self,
        *,
        intent: dict[str, Any],
        aspects: list[str] | None = None,
        vector: list[float] | None = None,
        parent_cast_id: str | None = None,
        causal_root_cast_id: str | None = None,
        thresholds: dict[str, Any] | None = None,
        effects: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        out = decision_tools.tool_decide(
            self,
            intent=intent,
            aspects=aspects,
            vector=vector,
            parent_cast_id=parent_cast_id,
            causal_root_cast_id=causal_root_cast_id,
            thresholds=thresholds,
            effects=effects,
        )
        decision = out.get("decision", {})
        cast = out.get("cast", {})
        self._emit_event(
            "decide",
            {
                "action": decision.get("action"),
                "rationale": decision.get("rationale"),
                "cast_id": cast.get("cast_id"),
            },
            cast_id=cast.get("cast_id"),
        )
        return out
    def tool_cast(
        self,
        aspects: list[str],
        intent: dict,
        *,
        parent_cast_id: str | None = None,
        branch_id: str | None = None,
        chained: bool = False,
        force: bool = False,
        include_arcane_transcript: bool = False,
    ) -> dict[str, Any]:
        out = casting_tools.tool_cast(
            self,
            aspects,
            intent,
            parent_cast_id=parent_cast_id,
            branch_id=branch_id,
            chained=chained,
            force=force,
            include_arcane_transcript=include_arcane_transcript,
        )
        self._emit_event(
            "cast",
            {
                "aspects": list(aspects),
                "verdict": out.get("verdict"),
                "adjusted_resonance": out.get("adjusted_resonance"),
            },
            cast_id=out.get("cast_id"),
            branch_id=branch_id,
        )
        return out
    def tool_fluid_cast(
        self,
        vector: list[float],
        intent: dict,
        *,
        parent_cast_id: str | None = None,
        branch_id: str | None = None,
        include_arcane_transcript: bool = False,
    ) -> dict[str, Any]:
        return casting_tools.tool_fluid_cast(
            self,
            vector,
            intent,
            parent_cast_id=parent_cast_id,
            branch_id=branch_id,
            include_arcane_transcript=include_arcane_transcript,
        )
    def _write_fluid_result_to_grimoire(self, result: CastResult) -> None:
        return casting_tools._write_fluid_result_to_grimoire(self, result)
    def tool_auto_cast(
        self,
        vector: list[float],
        intent: dict,
        *,
        max_depth: int = 5,
        target_resonance: float = 0.75,
        blend_alpha: float = 0.35,
        include_diagnostics: bool = False,
        include_arcane_transcript: bool = False,
    ) -> dict[str, Any]:
        out = casting_tools.tool_auto_cast(
            self,
            vector,
            intent,
            max_depth=max_depth,
            target_resonance=target_resonance,
            blend_alpha=blend_alpha,
            include_diagnostics=include_diagnostics,
            include_arcane_transcript=include_arcane_transcript,
        )
        chain = out.get("auto_cast_chain") or []
        for idx, row in enumerate(chain, start=1):
            self._emit_event(
                "auto_cast_step",
                {
                    "step": idx,
                    "adjusted_resonance": row.get("adjusted_resonance"),
                    "verdict": row.get("verdict"),
                },
                cast_id=row.get("cast_id"),
            )
        return out
    def tool_swarm_join(
        self,
        swarm_id: str,
        session_id: str,
        *,
        consensus_threshold: float = 0.75,
    ) -> dict[str, Any]:
        return swarm_tools.tool_swarm_join(
            self,
            swarm_id,
            session_id,
            consensus_threshold=consensus_threshold,
        )
    def tool_swarm_cast(
        self,
        swarm_id: str,
        session_id: str,
        vector: list[float],
        intent: dict,
        *,
        consensus_threshold: float | None = None,
    ) -> dict[str, Any]:
        return swarm_tools.tool_swarm_cast(
            self,
            swarm_id,
            session_id,
            vector,
            intent,
            consensus_threshold=consensus_threshold,
        )
    def tool_swarm_status(self, swarm_id: str) -> dict[str, Any]:
        return swarm_tools.tool_swarm_status(self, swarm_id)
    def tool_gossip_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        return swarm_tools.tool_gossip_sync(self, payload)
    def tool_channel_status(self, branch_id: str) -> dict[str, Any]:
        return drift_tools.tool_channel_status(self, branch_id)
    def tool_sync_channel(self, branch_id: str) -> dict[str, Any]:
        return drift_tools.tool_sync_channel(self, branch_id)
    def tool_geometric_cast(
        self,
        payload: list[float],
        *,
        version: int = 1,
        branch_id: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        return casting_tools.tool_geometric_cast(
            self,
            payload,
            version=version,
            branch_id=branch_id,
            force=force,
        )

    # ---------------------------------------------------------------------
    # Session Codec V2 helpers (transport-agnostic)
    # ---------------------------------------------------------------------
    def session_open(
        self,
        *,
        transport: str,
        local_peer_id: str,
        local_key_id: str,
        remote_peer_id: str,
        remote_key_id: str,
        codec_version: int = 2,
        proof_scheme: str = "SIGNED",
        aspect_dimensionality: int = 6,
        max_packet_bytes: int | None = None,
        channel_branch_id: str | None = None,
        anchor_cast_id: str | None = None,
        signing_secret: bytes | None = None,
    ) -> dict[str, Any]:
        return session_tools.session_open(
            self,
            transport=transport,
            local_peer_id=local_peer_id,
            local_key_id=local_key_id,
            remote_peer_id=remote_peer_id,
            remote_key_id=remote_key_id,
            codec_version=codec_version,
            proof_scheme=proof_scheme,
            aspect_dimensionality=aspect_dimensionality,
            max_packet_bytes=max_packet_bytes,
            channel_branch_id=channel_branch_id,
            anchor_cast_id=anchor_cast_id,
            signing_secret=signing_secret,
        )
    def session_apply_packet(self, packet_dict: dict[str, Any]) -> dict[str, Any]:
        return session_tools.session_apply_packet(self, packet_dict)
    def session_checkpoint(self, session_id: str) -> dict[str, Any]:
        return session_tools.session_checkpoint(self, session_id)
    def session_rewind_to(self, session_id: str, sequence: int) -> dict[str, Any]:
        return session_tools.session_rewind_to(self, session_id, sequence)
    def session_replay_from(self, session_id: str, sequence: int, *, limit: int = 100) -> dict[str, Any]:
        return session_tools.session_replay_from(
            self,
            session_id,
            sequence,
            limit=limit,
        )
    def session_fork(self, session_id: str, from_sequence: int, *, new_transport: str | None = None) -> dict[str, Any]:
        return session_tools.session_fork(
            self,
            session_id,
            from_sequence,
            new_transport=new_transport,
        )
    def session_encode_packet(
        self,
        *,
        session_id: str,
        sequence: int,
        packet_type: str,
        payload: dict,
    ) -> dict[str, Any]:
        return session_tools.session_encode_packet(
            self,
            session_id=session_id,
            sequence=sequence,
            packet_type=packet_type,
            payload=payload,
        )
    def tool_crystallized_sigils(self) -> list[dict[str, Any]]:
        return seed_tools.tool_crystallized_sigils(self)
    def tool_divergence(self, cast_id: str) -> dict[str, Any]:
        return drift_tools.tool_divergence(self, cast_id)
    def tool_set_divergence_thresholds(self, payload: dict) -> dict[str, Any]:
        return drift_tools.tool_set_divergence_thresholds(self, payload)
    def tool_divergence_thresholds(self) -> dict[str, Any]:
        return drift_tools.tool_divergence_thresholds(self)
    def tool_divergence_reports(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        return drift_tools.tool_divergence_reports(
            self,
            status=status,
            limit=limit,
            since=since,
        )
    def tool_drift_branches(self, *, limit: int = 25) -> list[dict[str, Any]]:
        return drift_tools.tool_drift_branches(self, limit=limit)
    def tool_lineage_drift(
        self, *, cast_id: str, max_depth: int = 50, top_k: int = 3
    ) -> dict[str, Any]:
        return drift_tools.tool_lineage_drift(
            self,
            cast_id=cast_id,
            max_depth=max_depth,
            top_k=top_k,
        )
    def tool_register_aspect(
        self, aspect_id: str, polarity: int, entropy_coefficient: float, symbol: str
    ) -> dict[str, Any]:
        return registry_tools.tool_register_aspect(
            self,
            aspect_id=aspect_id,
            polarity=polarity,
            entropy_coefficient=entropy_coefficient,
            symbol=symbol,
        )
    def tool_register_sigil(self, payload: dict) -> dict[str, Any]:
        return registry_tools.tool_register_sigil(self, payload)
    def tool_registered_aspects(self) -> list[dict[str, Any]]:
        return registry_tools.tool_registered_aspects(self)
    def tool_registered_sigils(self) -> list[dict[str, Any]]:
        return registry_tools.tool_registered_sigils(self)
    def tool_query(self, filters: dict) -> list[dict[str, Any]]:
        return query_tools.tool_query(self, filters)
    def tool_semantic_search(
        self, proximity_vector: list[float], threshold: float, limit: int
    ) -> list[dict[str, Any]]:
        return query_tools.tool_semantic_search(
            self,
            proximity_vector,
            threshold,
            limit,
        )
    def tool_inspect(self, cast_id: str) -> dict[str, Any]:
        return query_tools.tool_inspect(self, cast_id)
    def tool_lineage(self, cast_id: str, max_depth: int = 50) -> list[dict[str, Any]]:
        return query_tools.tool_lineage(self, cast_id, max_depth=max_depth)
    def tool_seeds(self, crystallized: Optional[bool]) -> list[dict[str, Any]]:
        return seed_tools.tool_seeds(self, crystallized)
