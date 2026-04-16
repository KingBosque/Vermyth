from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

from vermyth.registry import AspectRegistry
from vermyth.schema import (
    CastNode,
    CastResult,
    ExecutionReceipt,
    NodeExecutionReceipt,
    NodeExecutionStatus,
    NodeType,
    ProgramExecution,
    ProgramStatus,
    RollbackStrategy,
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
    receipt_nodes: list[NodeExecutionReceipt] = []
    started_at = datetime.now(timezone.utc)
    rollback_queue: list[CastNode] = []

    def _eval_condition(expr: Any, context: dict[str, Any]) -> bool:
        if expr is None:
            return True
        op = str(getattr(expr, "op", "exists"))
        key = str(getattr(expr, "key", ""))
        value = getattr(expr, "value", None)
        if not key:
            return False
        got = context.get(key)
        if op == "exists":
            return key in context
        if op == "eq":
            return got == value
        if op == "neq":
            return got != value
        if op == "gt":
            return got is not None and got > value
        if op == "gte":
            return got is not None and got >= value
        if op == "lt":
            return got is not None and got < value
        if op == "lte":
            return got is not None and got <= value
        if op == "contains":
            return got is not None and value in got
        return False

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
        node_started = datetime.now(timezone.utc)
        pre_results: list[dict[str, Any]] = []
        post_results: list[dict[str, Any]] = []
        retries = 0
        effect_summary = [e.model_dump(mode="json") for e in (node.effects or [])]

        if node.preconditions:
            pre_context = {
                "pred_count": len(pred_results),
                "has_parent": parent_result is not None,
            }
            pre_ok = True
            for cond in node.preconditions:
                ok = _eval_condition(cond.expr, pre_context)
                pre_results.append(
                    {
                        "predicate": cond.predicate,
                        "ok": bool(ok),
                    }
                )
                if not ok:
                    pre_ok = False
            if not pre_ok:
                blocked.update(node.successors)
                receipt_nodes.append(
                    NodeExecutionReceipt(
                        node_id=node_id,
                        status=NodeExecutionStatus.SKIPPED,
                        started_at=node_started,
                        duration_ms=max(
                            0,
                            int(
                                (datetime.now(timezone.utc) - node_started).total_seconds()
                                * 1000
                            ),
                        ),
                        precondition_results=pre_results,
                        postcondition_results=[],
                        retries=0,
                        effect_summary=effect_summary,
                        error="precondition_failed",
                    )
                )
                continue

        base: CastResult | None = None
        run_error: str | None = None
        attempts = int(node.retry_policy.max_attempts) if node.retry_policy else 1
        backoff_ms = int(node.retry_policy.backoff_ms) if node.retry_policy else 0
        for attempt in range(1, attempts + 1):
            try:
                retries = attempt - 1
                if node.node_type == NodeType.GATE:
                    gate_ok = any(
                        r.verdict.verdict_type == node.gate_condition for r in pred_results
                    )
                    if not gate_ok:
                        blocked.update(node.successors)
                    receipt_nodes.append(
                        NodeExecutionReceipt(
                            node_id=node_id,
                            status=NodeExecutionStatus.OK if gate_ok else NodeExecutionStatus.SKIPPED,
                            started_at=node_started,
                            duration_ms=max(
                                0,
                                int(
                                    (datetime.now(timezone.utc) - node_started).total_seconds()
                                    * 1000
                                ),
                            ),
                            precondition_results=pre_results,
                            postcondition_results=[],
                            retries=retries,
                            effect_summary=effect_summary,
                        )
                    )
                    base = None
                    break
                elif node.node_type == NodeType.MERGE:
                    if not pred_results:
                        base = None
                        break
                    if node.merge_strategy == "FIRST_COHERENT":
                        merged = next(
                            (
                                r
                                for r in pred_results
                                if r.verdict.verdict_type == VerdictType.COHERENT
                            ),
                            pred_results[0],
                        )
                    else:
                        merged = max(pred_results, key=lambda r: float(r.verdict.resonance.adjusted))
                    results_by_node[node_id] = merged
                    node_results[node_id] = merged.cast_id
                    receipt_nodes.append(
                        NodeExecutionReceipt(
                            node_id=node_id,
                            status=NodeExecutionStatus.OK,
                            started_at=node_started,
                            duration_ms=max(
                                0,
                                int(
                                    (datetime.now(timezone.utc) - node_started).total_seconds()
                                    * 1000
                                ),
                            ),
                            precondition_results=pre_results,
                            postcondition_results=[],
                            retries=retries,
                            effect_summary=effect_summary,
                        )
                    )
                    base = None
                    break
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
                break
            except Exception as exc:
                run_error = str(exc)
                if attempt >= attempts:
                    base = None
                    break
                if backoff_ms > 0:
                    time.sleep(float(backoff_ms) / 1000.0)

        if node.node_type in (NodeType.GATE, NodeType.MERGE):
            continue
        if base is None:
            status = ProgramStatus.FAILED
            receipt_nodes.append(
                NodeExecutionReceipt(
                    node_id=node_id,
                    status=NodeExecutionStatus.FAILED,
                    started_at=node_started,
                    duration_ms=max(
                        0,
                        int((datetime.now(timezone.utc) - node_started).total_seconds() * 1000),
                    ),
                    precondition_results=pre_results,
                    postcondition_results=post_results,
                    retries=retries,
                    effect_summary=effect_summary,
                    error=run_error or "execution_failed",
                )
            )
            for prev in reversed(rollback_queue):
                rb_started = datetime.now(timezone.utc)
                receipt_nodes.append(
                    NodeExecutionReceipt(
                        node_id=prev.node_id,
                        status=NodeExecutionStatus.ROLLED_BACK,
                        started_at=rb_started,
                        duration_ms=0,
                        precondition_results=[],
                        postcondition_results=[],
                        retries=0,
                        effect_summary=[],
                        error=(
                            "rollback:none"
                            if prev.rollback in (None, RollbackStrategy.NONE)
                            else f"rollback:{prev.rollback.value.lower()}"
                        ),
                    )
                )
            break

        result = (
            engine._cast_result_with_lineage(base, parent_result, branch_id)
            if parent_result is not None
            else base
        )
        results_by_node[node_id] = result
        node_results[node_id] = result.cast_id
        rollback_queue.append(node)

        if node.postconditions:
            post_context = {
                "adjusted_resonance": float(result.verdict.resonance.adjusted),
                "verdict": result.verdict.verdict_type.value,
            }
            for cond in node.postconditions:
                ok = _eval_condition(cond.expr, post_context)
                post_results.append({"predicate": cond.predicate, "ok": bool(ok)})
        receipt_nodes.append(
            NodeExecutionReceipt(
                node_id=node_id,
                status=NodeExecutionStatus.OK,
                started_at=node_started,
                duration_ms=max(
                    0,
                    int((datetime.now(timezone.utc) - node_started).total_seconds() * 1000),
                ),
                precondition_results=pre_results,
                postcondition_results=post_results,
                retries=retries,
                effect_summary=effect_summary,
            )
        )

    completed_at = datetime.now(timezone.utc)
    execution = ProgramExecution(
        program_id=compiled.program_id,
        status=status,
        node_results=node_results,
        started_at=started_at,
        completed_at=completed_at,
        branch_id=branch_id,
    )
    engine._last_execution_receipt = ExecutionReceipt(
        execution_id=execution.execution_id,
        program_id=compiled.program_id,
        status=status,
        nodes=receipt_nodes,
        started_at=started_at,
        completed_at=completed_at,
    )
    return execution
