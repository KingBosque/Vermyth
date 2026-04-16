from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from vermyth.bootstrap import build_tools
from vermyth.schema import (
    AspectID,
    CastNode,
    EmergentAspect,
    EffectClass,
    GenesisStatus,
    Intent,
    NodeType,
    ProgramStatus,
    ReversibilityClass,
    SemanticProgram,
    SemanticVector,
    SideEffectTolerance,
    VerdictType,
)


def _base_intent() -> dict[str, str]:
    return {
        "objective": "Stabilize an explainable cast trajectory",
        "scope": "local example",
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "LOW",
    }


def main() -> None:
    with TemporaryDirectory() as td:
        db_path = Path(td) / "example.db"
        grimoire, _composition, engine, tools = build_tools(db_path=db_path)

        # 1) Register an aspect extension.
        registered = tools.tool_register_aspect("ECHO", 1, 0.40, "✧")
        print("registered aspect:", registered["name"])

        # 2) Cast repeatedly to create seed history.
        cast_payload = None
        for _ in range(12):
            cast_payload = tools.tool_cast(["MIND", "LIGHT"], _base_intent())
        assert cast_payload is not None
        print("last cast:", cast_payload["cast_id"])

        # 3) Exercise accumulate -> crystallize.
        seeds = grimoire.query_seeds(aspect_pattern=frozenset({AspectID.MIND, AspectID.LIGHT}))
        if seeds:
            candidate = engine.crystallize(seeds[0])
            if candidate is not None:
                print("crystallized sigil:", candidate.name)
            else:
                print("no crystallized sigil produced in this run")

        # 4) Compile + execute a tiny semantic program.
        intent_obj = Intent(
            objective="Program node cast",
            scope="example",
            reversibility=ReversibilityClass.REVERSIBLE,
            side_effect_tolerance=SideEffectTolerance.LOW,
        )
        program = SemanticProgram(
            name="example-program",
            status=ProgramStatus.DRAFT,
            entry_node_ids=["n1"],
            nodes=[
                CastNode(
                    node_id="n1",
                    node_type=NodeType.CAST,
                    aspects=["MIND", "LIGHT"],
                    intent=intent_obj,
                    successors=[],
                )
            ],
        )
        compiled = tools.tool_compile_program(program.model_dump(mode="json"))
        execution = tools.tool_execute_program(compiled["program_id"])
        print("program execution:", execution["execution_id"])

        # 5) Propose + accept genesis (fallback inserts deterministic proposal).
        proposals = tools.tool_propose_genesis(
            history_limit=200,
            min_cluster_size=1,
            min_unexplained_variance=0.0,
        )
        if not proposals:
            fallback = EmergentAspect(
                proposed_name="GENESIS_EXAMPLE",
                derived_polarity=1,
                derived_entropy=0.25,
                proposed_symbol="✶",
                centroid_vector=SemanticVector(components=(0.0, 0.0, 0.0, 1.0, 0.0, 0.2, 0.1)),
                support_count=1,
                mean_resonance=0.8,
                coherence_rate=1.0,
                status=GenesisStatus.PROPOSED,
                evidence_cast_ids=[cast_payload["cast_id"]],
            )
            grimoire.write_emergent_aspect(fallback)
            proposals = [fallback.model_dump(mode="json")]
        accepted = tools.tool_accept_genesis(proposals[0]["genesis_id"])
        print("accepted genesis:", accepted["proposed_name"])

        # Keep output compact and obvious for quick smoke runs.
        print("done")


if __name__ == "__main__":
    main()
