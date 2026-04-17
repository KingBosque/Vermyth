from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vermyth.engine.operations.program_validation import validate_program
from vermyth.schema import (
    CastNode,
    Effect,
    Intent,
    NodeType,
    Postcondition,
    ProgramStatus,
    ReversibilityClass,
    SemanticProgram,
    SideEffectTolerance,
    VerdictType,
)


def _intent() -> Intent:
    return Intent(
        objective="x",
        scope="y",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )


def test_validate_duplicate_postcondition_warning():
    n = CastNode(
        node_id="n1",
        node_type=NodeType.CAST,
        aspects=["MIND"],
        intent=_intent(),
        postconditions=[
            Postcondition(predicate="p1"),
            Postcondition(predicate="p1"),
        ],
        successors=[],
    )
    p = SemanticProgram(
        name="dup-post",
        nodes=[n],
        entry_node_ids=["n1"],
    )
    r = validate_program(p)
    assert r.ok
    assert any("duplicate postcondition" in w for w in r.warnings)


def test_validate_gate_dead_end_warning():
    g = CastNode(
        node_id="g1",
        node_type=NodeType.GATE,
        intent=_intent(),
        gate_condition=VerdictType.COHERENT,
        aspects=None,
        vector=None,
        successors=[],
    )
    p = SemanticProgram(
        name="gate-dead",
        nodes=[g],
        entry_node_ids=["g1"],
    )
    r = validate_program(p)
    assert r.ok
    assert any("GATE with no successors" in w for w in r.warnings)


def test_validate_effect_missing_type_errors():
    bad_effect = Effect.model_construct(effect_type=None)
    n = CastNode.model_construct(
        node_id="n1",
        node_type=NodeType.CAST,
        aspects=["MIND"],
        intent=_intent(),
        successors=[],
        effects=[bad_effect],
    )
    now = datetime.now(timezone.utc)
    p = SemanticProgram.model_construct(
        program_id="p1",
        name="bad-eff",
        status=ProgramStatus.DRAFT,
        nodes=[n],
        entry_node_ids=["n1"],
        metadata={},
        created_at=now,
        updated_at=now,
    )
    r = validate_program(p)
    assert not r.ok
    assert any("effect missing effect_type" in e for e in r.errors)


def test_compile_program_rejects_invalid_effect(make_tools):
    bad_effect = Effect.model_construct(effect_type=None)
    n = CastNode.model_construct(
        node_id="n1",
        node_type=NodeType.CAST,
        aspects=["MIND"],
        intent=_intent(),
        successors=[],
        effects=[bad_effect],
    )
    now = datetime.now(timezone.utc)
    p = SemanticProgram.model_construct(
        program_id="p1",
        name="bad-eff",
        status=ProgramStatus.DRAFT,
        nodes=[n],
        entry_node_ids=["n1"],
        metadata={},
        created_at=now,
        updated_at=now,
    )
    with pytest.raises(ValueError, match="program validation failed"):
        make_tools._engine.compile_program(p)


def test_execute_program_denies_warnings_when_env(make_tools, monkeypatch):
    monkeypatch.setenv("VERMYTH_DENY_PROGRAM_VALIDATION_WARNINGS", "1")
    payload = {
        "name": "warn-run",
        "nodes": [
            {
                "node_id": "n1",
                "node_type": "CAST",
                "aspects": ["MIND"],
                "intent": {
                    "objective": "x",
                    "scope": "y",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "successors": [],
                "effects": [
                    {
                        "effect_type": "NETWORK",
                        "target": {
                            "kind": "http",
                            "uri": "https://example.com",
                            "scope": "network",
                            "access": "READ",
                        },
                        "reversible": False,
                        "cost_hint": 1.0,
                    }
                ],
            },
        ],
        "entry_node_ids": ["n1"],
    }
    compiled = make_tools.tool_compile_program(payload)
    with pytest.raises(ValueError, match="program validation warnings"):
        make_tools.tool_execute_program(compiled["program_id"])
