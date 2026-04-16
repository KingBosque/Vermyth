from __future__ import annotations

from datetime import datetime, timezone

from ulid import ULID

from vermyth.registry import AspectRegistry
from vermyth.schema import (
    CastNode,
    CastResult,
    NodeType,
    ProgramExecution,
    ProgramStatus,
    SemanticProgram,
    VerdictType,
)


def topological_order(
    engine, nodes: dict[str, CastNode], predecessors: dict[str, list[str]]
) -> list[str]:
    _ = engine
    indegree: dict[str, int] = {nid: len(preds) for nid, preds in predecessors.items()}
    ready = sorted([nid for nid, d in indegree.items() if d == 0])
    out: list[str] = []
    while ready:
        cur = ready.pop(0)
        out.append(cur)
        for nxt in nodes[cur].successors:
            indegree[nxt] = int(indegree[nxt]) - 1
            if indegree[nxt] == 0:
                ready.append(nxt)
                ready.sort()
    if len(out) != len(nodes):
        raise ValueError("semantic program contains a cycle")
    return out


def compile_program(engine, program: SemanticProgram) -> SemanticProgram:
    nodes = {n.node_id: n for n in program.nodes}
    predecessors: dict[str, list[str]] = {nid: [] for nid in nodes}
    for node in program.nodes:
        for succ in node.successors:
            if succ not in nodes:
                raise ValueError(f"node {node.node_id} references unknown successor {succ}")
            predecessors[succ].append(node.node_id)

    topological_order(engine, nodes, predecessors)
    now = datetime.now(timezone.utc)
    return SemanticProgram.model_construct(
        program_id=program.program_id,
        name=program.name,
        status=ProgramStatus.COMPILED,
        nodes=program.nodes,
        entry_node_ids=program.entry_node_ids,
        metadata=program.metadata,
        created_at=program.created_at,
        updated_at=now,
    )


def execute_program(engine, program: SemanticProgram) -> ProgramExecution:
    compiled = (
        program if program.status == ProgramStatus.COMPILED else compile_program(engine, program)
    )
    nodes = {n.node_id: n for n in compiled.nodes}
    predecessors: dict[str, list[str]] = {nid: [] for nid in nodes}
    for node in compiled.nodes:
        for succ in node.successors:
            predecessors[succ].append(node.node_id)
    order = topological_order(engine, nodes, predecessors)

    registry = AspectRegistry.get()
    branch_id = str(ULID())
    blocked: set[str] = set()
    results_by_node: dict[str, CastResult] = {}
    status = ProgramStatus.COMPLETED
    node_results: dict[str, str] = {}

    for node_id in order:
        if node_id in blocked:
            continue
        node = nodes[node_id]
        pred_results = [results_by_node[p] for p in predecessors[node_id] if p in results_by_node]
        parent_result = (
            max(pred_results, key=lambda r: float(r.verdict.resonance.adjusted))
            if pred_results
            else None
        )

        try:
            if node.node_type == NodeType.GATE:
                gate_ok = any(
                    r.verdict.verdict_type == node.gate_condition for r in pred_results
                )
                if not gate_ok:
                    blocked.update(node.successors)
                continue
            elif node.node_type == NodeType.MERGE:
                if not pred_results:
                    continue
                if node.merge_strategy == "FIRST_COHERENT":
                    merged = next(
                        (r for r in pred_results if r.verdict.verdict_type == VerdictType.COHERENT),
                        pred_results[0],
                    )
                else:
                    merged = max(pred_results, key=lambda r: float(r.verdict.resonance.adjusted))
                results_by_node[node_id] = merged
                node_results[node_id] = merged.cast_id
                continue
            else:
                if node.node_type == NodeType.CAST:
                    resolved = frozenset(registry.resolve(n) for n in (node.aspects or []))
                    sigil = engine.composition_engine.compose(resolved)
                    verdict = engine.evaluate(sigil, node.intent)
                    base = CastResult(intent=node.intent, sigil=sigil, verdict=verdict)
                elif node.node_type == NodeType.FLUID_CAST:
                    if node.vector is None:
                        raise ValueError("FLUID_CAST node missing vector")
                    base = engine.fluid_cast(node.vector, node.intent)
                elif node.node_type == NodeType.AUTO_CAST:
                    if node.vector is None:
                        raise ValueError("AUTO_CAST node missing vector")
                    base, _ = engine.auto_cast(node.vector, node.intent)
                else:
                    raise ValueError(f"unsupported node type {node.node_type.value}")
        except Exception:
            status = ProgramStatus.FAILED
            break

        result = (
            engine._cast_result_with_lineage(base, parent_result, branch_id)
            if parent_result is not None
            else base
        )
        results_by_node[node_id] = result
        node_results[node_id] = result.cast_id

    completed_at = datetime.now(timezone.utc)
    return ProgramExecution(
        program_id=compiled.program_id,
        status=status,
        node_results=node_results,
        started_at=compiled.updated_at,
        completed_at=completed_at,
        branch_id=branch_id,
    )
