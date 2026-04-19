"""Vermyth CLI: human-readable inspection and debugging."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from vermyth.contracts import CLIContract
from vermyth.engine.resonance import ResonanceEngine
from vermyth.cli.commands import auto_cast as auto_cast_command
from vermyth.cli.commands import cast as cast_command
from vermyth.cli.commands import causal as causal_command
from vermyth.cli.commands import decide as decide_command
from vermyth.cli.commands import drift as drift_command
from vermyth.cli.commands import genesis as genesis_command
from vermyth.cli import parser as cli_parser
from vermyth.cli.commands import programs as program_command
from vermyth.cli.commands import query as query_command
from vermyth.cli.commands import registry as registry_command
from vermyth.cli.commands import swarm as swarm_command
from vermyth.bootstrap import build_tools, build_tools_from_env
from vermyth.engine.projection_backends import NullProjectionBackend
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.tools import VermythTools
from vermyth.registry import AspectRegistry
from vermyth.schema import DivergenceReport
from vermyth.mcp.geometric import decode_packet, encode_packet
from vermyth.schema import GeometricPacket, Intent, SemanticVector, ReversibilityClass, SideEffectTolerance
class VermythCLI(CLIContract):
    """Command-line interface over VermythTools."""
    def __init__(
        self,
        engine: ResonanceEngine | None = None,
        grimoire: Grimoire | None = None,
    ) -> None:
        if engine is not None and grimoire is not None:
            self._engine = engine
            self._grimoire = grimoire
        else:
            try:
                self._grimoire, _composition, self._engine, self._tools = build_tools_from_env(
                    None
                )
            except ValueError as exc:
                print(f"[vermyth] invalid backend configuration: {exc}", file=sys.stderr)
                self._grimoire, _composition, self._engine, self._tools = build_tools(
                    None, backend=NullProjectionBackend()
                )
        if not hasattr(self, "_tools"):
            self._tools = VermythTools(self._engine, self._grimoire)
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
        fail_on_diverged: bool = False,
        chained: bool = False,
        force: bool = False,
        include_arcane_transcript: bool = False,
    ) -> None:
        return cast_command.cmd_cast(
            self,
            aspects,
            objective,
            scope,
            reversibility,
            side_effect_tolerance,
            parent_cast_id=parent_cast_id,
            branch_id=branch_id,
            fail_on_diverged=fail_on_diverged,
            chained=chained,
            force=force,
            include_arcane_transcript=include_arcane_transcript,
        )
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
        policy_model: str | None = None,
        tuned_thresholds_path: str | None = None,
    ) -> None:
        return decide_command.cmd_decide(
            self,
            objective=objective,
            scope=scope,
            reversibility=reversibility,
            side_effect_tolerance=side_effect_tolerance,
            aspects=aspects,
            vector=vector,
            parent_cast_id=parent_cast_id,
            causal_root_cast_id=causal_root_cast_id,
            policy_model=policy_model,
            tuned_thresholds_path=tuned_thresholds_path,
        )
    def cmd_fluid_cast(
        self,
        vector: list[float],
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
        *,
        parent_cast_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        fail_on_diverged: bool = False,
        include_arcane_transcript: bool = False,
    ) -> None:
        return cast_command.cmd_fluid_cast(
            self,
            vector,
            objective,
            scope,
            reversibility,
            side_effect_tolerance,
            parent_cast_id=parent_cast_id,
            branch_id=branch_id,
            fail_on_diverged=fail_on_diverged,
            include_arcane_transcript=include_arcane_transcript,
        )
    def cmd_auto_cast(
        self,
        vector: list[float],
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
        *,
        max_depth: int = 5,
        target_resonance: float = 0.75,
        blend_alpha: float = 0.35,
        trace: bool = False,
        include_arcane_transcript: bool = False,
    ) -> None:
        return auto_cast_command.cmd_auto_cast(
            self,
            vector,
            objective,
            scope,
            reversibility,
            side_effect_tolerance,
            max_depth=max_depth,
            target_resonance=target_resonance,
            blend_alpha=blend_alpha,
            trace=trace,
            include_arcane_transcript=include_arcane_transcript,
        )
    def cmd_swarm_join(
        self, swarm_id: str, session_id: str, *, consensus_threshold: float = 0.75
    ) -> None:
        return swarm_command.cmd_swarm_join(
            self,
            swarm_id=swarm_id,
            session_id=session_id,
            consensus_threshold=consensus_threshold,
        )
    def cmd_swarm_cast(
        self,
        swarm_id: str,
        session_id: str,
        vector: list[float],
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
        *,
        consensus_threshold: Optional[float] = None,
    ) -> None:
        return swarm_command.cmd_swarm_cast(
            self,
            swarm_id=swarm_id,
            session_id=session_id,
            vector=vector,
            objective=objective,
            scope=scope,
            reversibility=reversibility,
            side_effect_tolerance=side_effect_tolerance,
            consensus_threshold=consensus_threshold,
        )
    def cmd_swarm_status(self, swarm_id: str) -> None:
        return swarm_command.cmd_swarm_status(self, swarm_id)
    def cmd_gossip_sync(self, path: str) -> None:
        return swarm_command.cmd_gossip_sync(self, path)
    def cmd_compile_program(self, path: str) -> None:
        return program_command.cmd_compile_program(self, path)
    def cmd_execute_program(self, program_id: str) -> None:
        return program_command.cmd_execute_program(self, program_id)
    def cmd_program_status(self, program_id: str) -> None:
        return program_command.cmd_program_status(self, program_id)
    def cmd_list_programs(self, limit: int = 50) -> None:
        return program_command.cmd_list_programs(self, int(limit))
    def cmd_execution_status(self, execution_id: str) -> None:
        return program_command.cmd_execution_status(self, execution_id)
    def cmd_execution_receipt(self, execution_id: str) -> None:
        return program_command.cmd_execution_receipt(self, execution_id)
    def cmd_receipt_verify(self, path: str, public_pem_path: str | None) -> None:
        return program_command.cmd_receipt_verify(self, path, public_pem_path)
    def cmd_propose_genesis(
        self,
        *,
        history_limit: int = 500,
        min_cluster_size: int = 15,
        min_unexplained_variance: float = 0.3,
        min_coherence_rate: float = 0.6,
    ) -> None:
        return genesis_command.cmd_propose_genesis(
            self,
            history_limit=history_limit,
            min_cluster_size=min_cluster_size,
            min_unexplained_variance=min_unexplained_variance,
            min_coherence_rate=min_coherence_rate,
        )
    def cmd_genesis_proposals(self, *, status: str | None = None, limit: int = 50) -> None:
        return genesis_command.cmd_genesis_proposals(self, status=status, limit=limit)
    def cmd_accept_genesis(self, genesis_id: str) -> None:
        return genesis_command.cmd_accept_genesis(self, genesis_id)
    def cmd_reject_genesis(self, genesis_id: str) -> None:
        return genesis_command.cmd_reject_genesis(self, genesis_id)
    def cmd_review_genesis(self, genesis_id: str, reviewer: str, note: str | None = None) -> None:
        return genesis_command.cmd_review_genesis(
            self,
            genesis_id=genesis_id,
            reviewer=reviewer,
            note=note,
        )
    def cmd_infer_cause(self, source_cast_id: str, target_cast_id: str) -> None:
        return causal_command.cmd_infer_cause(self, source_cast_id, target_cast_id)
    def cmd_add_cause(self, payload: dict[str, object]) -> None:
        return causal_command.cmd_add_cause(self, payload)
    def cmd_causal_graph(
        self,
        *,
        root_cast_id: str,
        edge_types: list[str] | None = None,
        direction: str = "both",
        max_depth: int = 5,
        min_weight: float = 0.0,
    ) -> None:
        return causal_command.cmd_causal_graph(
            self,
            root_cast_id=root_cast_id,
            edge_types=edge_types,
            direction=direction,
            max_depth=max_depth,
            min_weight=min_weight,
        )
    def cmd_evaluate_narrative(self, edge_ids: list[str]) -> None:
        return causal_command.cmd_evaluate_narrative(self, edge_ids)
    def cmd_predictive_cast(
        self,
        *,
        root_cast_id: str,
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
    ) -> None:
        return causal_command.cmd_predictive_cast(
            self,
            root_cast_id=root_cast_id,
            objective=objective,
            scope=scope,
            reversibility=reversibility,
            side_effect_tolerance=side_effect_tolerance,
        )
    def cmd_query(
        self,
        verdict: Optional[str],
        min_resonance: Optional[float],
        branch_id: Optional[str],
        limit: int,
    ) -> None:
        return query_command.cmd_query(
            self,
            verdict_filter=verdict,
            min_resonance=min_resonance,
            branch_id=branch_id,
            limit=limit,
        )
    def cmd_search(self, vector: list[float], threshold: float, limit: int) -> None:
        return query_command.cmd_search(self, vector, threshold, limit)
    def cmd_inspect(self, cast_id: str) -> None:
        return query_command.cmd_inspect(self, cast_id)
    def cmd_seeds(self, crystallized: Optional[bool]) -> None:
        return query_command.cmd_seeds(self, crystallized)
    def cmd_lineage(self, cast_id: str, max_depth: int) -> None:
        return query_command.cmd_lineage(self, cast_id, max_depth)
    def cmd_crystallized_sigils(self) -> None:
        return query_command.cmd_crystallized_sigils(self)
    def cmd_register_aspect(
        self, aspect_id: str, polarity: int, entropy_coefficient: float, symbol: str
    ) -> None:
        return registry_command.cmd_register_aspect(
            self,
            aspect_id=aspect_id,
            polarity=polarity,
            entropy_coefficient=entropy_coefficient,
            symbol=symbol,
        )
    def cmd_register_sigil(self, payload: dict) -> None:
        return registry_command.cmd_register_sigil(self, payload)
    def cmd_aspects(self) -> None:
        return registry_command.cmd_aspects(self)
    def cmd_registered_sigils(self) -> None:
        return registry_command.cmd_registered_sigils(self)
    def cmd_divergence(self, cast_id: str) -> None:
        return drift_command.cmd_divergence(self, cast_id)
    def cmd_set_thresholds(
        self,
        l2_stable: Optional[float],
        l2_diverged: Optional[float],
        cosine_stable: Optional[float],
        cosine_diverged: Optional[float],
    ) -> None:
        return drift_command.cmd_set_thresholds(
            self,
            l2_stable_max=l2_stable,
            l2_diverged_min=l2_diverged,
            cosine_stable_max=cosine_stable,
            cosine_diverged_min=cosine_diverged,
        )
    def cmd_thresholds(self) -> None:
        return drift_command.cmd_thresholds(self)
    def cmd_divergences(
        self,
        status: Optional[str],
        limit: int,
        since: Optional[str],
    ) -> None:
        return drift_command.cmd_divergences(
            self,
            status=status,
            limit=limit,
            since=since,
        )
    def cmd_drift_branches(self, limit: int) -> None:
        return drift_command.cmd_drift_branches(self, limit)
    def cmd_lineage_drift(self, cast_id: str, max_depth: int, top_k: int) -> None:
        return drift_command.cmd_lineage_drift(self, cast_id, max_depth, top_k)
    def cmd_backfill_divergence(self, limit: int) -> None:
        return drift_command.cmd_backfill_divergence(self, limit)
    def cmd_geometric_cast(
        self, payload: list[float], *, version: int = 1, branch_id: str | None = None, force: bool = False
    ) -> None:
        try:
            out = self._tools.tool_geometric_cast(
                payload=payload, version=int(version), branch_id=branch_id, force=bool(force)
            )
            print(out)
        except (ValueError, RuntimeError) as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    def cmd_encode(
        self,
        *,
        vector: list[float],
        objective: str,
        scope: str,
        reversibility: str,
        side_effect_tolerance: str,
    ) -> None:
        intent = Intent(
            objective=str(objective),
            scope=str(scope),
            reversibility=ReversibilityClass[str(reversibility)],
            side_effect_tolerance=SideEffectTolerance[str(side_effect_tolerance)],
        )
        vec = SemanticVector(components=tuple(float(x) for x in vector))
        packet = encode_packet(vec, intent, lineage=None)
        print({"version": packet.version, "payload": list(packet.payload)})
    def cmd_decode(self, *, payload: list[float], version: int = 1) -> None:
        packet = GeometricPacket(payload=tuple(float(x) for x in payload), version=int(version))
        vec, intent, lineage = decode_packet(packet)
        print(
            {
                "vector": [round(c, 6) for c in vec.components],
                "intent": {
                    "objective": intent.objective,
                    "scope": intent.scope,
                    "reversibility": intent.reversibility.name,
                    "side_effect_tolerance": intent.side_effect_tolerance.name,
                },
                "lineage": lineage.model_dump() if lineage is not None else None,
                "proof_valid": packet.validate_proof(),
            }
        )
    def build_parser(self) -> argparse.ArgumentParser:
        return cli_parser.build_parser()
    def run(self, args: list[str] | None = None) -> None:
        return cli_parser.run(self, args)

def main() -> None:
    VermythCLI().run()

if __name__ == "__main__":
    main()
