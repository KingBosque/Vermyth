from __future__ import annotations

from vermyth.schema import Intent, ReversibilityClass, SemanticVector, SideEffectTolerance


def _intent() -> Intent:
    return Intent(
        objective="trace iterative cast convergence",
        scope="tests",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )


def test_engine_auto_cast_with_diagnostics(resonance_engine):
    vec = SemanticVector(components=(0.2, 0.1, 0.0, 0.7, 0.0, 0.6))
    final, chain, diagnostics = resonance_engine.auto_cast(
        vec,
        _intent(),
        max_depth=4,
        with_diagnostics=True,
    )
    assert len(chain) >= 1
    assert diagnostics.final_adjusted == final.verdict.resonance.adjusted
    assert len(diagnostics.steps) == len(chain)


def test_tool_auto_cast_includes_diagnostics(make_tools, valid_intent):
    out = make_tools.tool_auto_cast(
        vector=[0.2, 0.1, 0.0, 0.7, 0.0, 0.6],
        intent=valid_intent,
        include_diagnostics=True,
    )
    assert "diagnostics" in out
    diag = out["diagnostics"]
    assert "steps" in diag
    assert isinstance(diag["steps"], list)
