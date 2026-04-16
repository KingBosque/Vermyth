from __future__ import annotations

from vermyth.schema import ProgramStatus


def _base_program(node_overrides: dict | None = None) -> dict:
    node = {
        "node_id": "n1",
        "node_type": "FLUID_CAST",
        "vector": {"components": [0, 0, 0, 1, 0, 1]},
        "intent": {
            "objective": "refine signal",
            "scope": "local",
            "reversibility": "PARTIAL",
            "side_effect_tolerance": "MEDIUM",
        },
        "successors": [],
    }
    if node_overrides:
        node.update(node_overrides)
    return {
        "name": "action-ir-test",
        "nodes": [node],
        "entry_node_ids": ["n1"],
        "metadata": {"suite": "action-ir"},
    }


def test_precondition_skip_records_receipt(make_tools):
    payload = _base_program(
        {
            "preconditions": [
                {
                    "predicate": "must_have_parent",
                    "expr": {"op": "eq", "key": "has_parent", "value": True},
                }
            ]
        }
    )
    compiled = make_tools.tool_compile_program(payload)
    execution = make_tools.tool_execute_program(compiled["program_id"])
    receipt = make_tools.tool_execution_receipt(execution["execution_id"])
    assert receipt["nodes"][0]["status"] == "SKIPPED"
    assert receipt["nodes"][0]["error"] == "precondition_failed"


def test_retry_success_records_retry_count(make_tools):
    payload = _base_program({"retry_policy": {"max_attempts": 2, "backoff_ms": 0}})
    compiled = make_tools.tool_compile_program(payload)

    calls = {"n": 0}
    original = make_tools._engine.fluid_cast

    def _flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return original(*args, **kwargs)

    make_tools._engine.fluid_cast = _flaky  # type: ignore[assignment]
    try:
        execution = make_tools.tool_execute_program(compiled["program_id"])
    finally:
        make_tools._engine.fluid_cast = original  # type: ignore[assignment]

    receipt = make_tools.tool_execution_receipt(execution["execution_id"])
    assert receipt["nodes"][0]["status"] == "OK"
    assert receipt["nodes"][0]["retries"] == 1


def test_retry_exhaustion_marks_failed(make_tools):
    payload = _base_program({"retry_policy": {"max_attempts": 2, "backoff_ms": 0}})
    compiled = make_tools.tool_compile_program(payload)

    def _always_fail(*args, **kwargs):
        raise RuntimeError("persistent")

    original = make_tools._engine.fluid_cast
    make_tools._engine.fluid_cast = _always_fail  # type: ignore[assignment]
    try:
        execution = make_tools.tool_execute_program(compiled["program_id"])
    finally:
        make_tools._engine.fluid_cast = original  # type: ignore[assignment]

    assert execution["status"] == ProgramStatus.FAILED.value
    receipt = make_tools.tool_execution_receipt(execution["execution_id"])
    assert receipt["nodes"][0]["status"] == "FAILED"


def test_postcondition_recorded(make_tools):
    payload = _base_program(
        {
            "postconditions": [
                {
                    "predicate": "high_resonance",
                    "expr": {"op": "gte", "key": "adjusted_resonance", "value": 0.0},
                }
            ]
        }
    )
    compiled = make_tools.tool_compile_program(payload)
    execution = make_tools.tool_execute_program(compiled["program_id"])
    receipt = make_tools.tool_execution_receipt(execution["execution_id"])
    assert receipt["nodes"][0]["status"] == "OK"
    assert receipt["nodes"][0]["postcondition_results"][0]["ok"] is True


def test_rollback_receipt_entries_on_failure(make_tools):
    payload = {
        "name": "rollback-test",
        "nodes": [
            {
                "node_id": "a",
                "node_type": "FLUID_CAST",
                "vector": {"components": [0, 0, 0, 1, 0, 1]},
                "intent": {
                    "objective": "start",
                    "scope": "local",
                    "reversibility": "PARTIAL",
                    "side_effect_tolerance": "MEDIUM",
                },
                "rollback": "COMPENSATE",
                "successors": ["b"],
            },
            {
                "node_id": "b",
                "node_type": "FLUID_CAST",
                "vector": {"components": [0, 0, 0, 1, 0, 1]},
                "intent": {
                    "objective": "fail",
                    "scope": "local",
                    "reversibility": "PARTIAL",
                    "side_effect_tolerance": "MEDIUM",
                },
                "retry_policy": {"max_attempts": 1, "backoff_ms": 0},
                "successors": [],
            },
        ],
        "entry_node_ids": ["a"],
        "metadata": {"suite": "action-ir"},
    }
    compiled = make_tools.tool_compile_program(payload)
    original = make_tools._engine.fluid_cast
    calls = {"n": 0}

    def _fail_second(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return original(*args, **kwargs)

    make_tools._engine.fluid_cast = _fail_second  # type: ignore[assignment]
    try:
        execution = make_tools.tool_execute_program(compiled["program_id"])
    finally:
        make_tools._engine.fluid_cast = original  # type: ignore[assignment]
    receipt = make_tools.tool_execution_receipt(execution["execution_id"])
    statuses = [n["status"] for n in receipt["nodes"]]
    assert "ROLLED_BACK" in statuses

