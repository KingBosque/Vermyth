from __future__ import annotations

from vermyth.schema import (
    AspectID,
    CausalSubgraph,
    Intent,
    ReversibilityClass,
    SideEffectTolerance,
)


def _intent() -> Intent:
    return Intent(
        objective="trace narrative provenance",
        scope="tests",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )


def test_predictive_cast_stamps_narrative_provenance(resonance_engine):
    graph = CausalSubgraph(
        root_cast_id="root-cast",
        nodes=["root-cast"],
        edges=[],
        narrative_coherence=0.8,
    )
    result = resonance_engine.predictive_cast(graph, _intent())
    assert result.provenance is not None
    assert result.provenance.narrative_coherence == 0.8
    assert result.provenance.causal_root_cast_id == "root-cast"


def test_decide_stamps_causal_context_provenance(resonance_engine, tmp_grimoire):
    decision, result = resonance_engine.decide(
        _intent(),
        aspects=frozenset({AspectID.MIND}),
        causal_root_cast_id="seed-root",
        grimoire=tmp_grimoire,
    )
    assert decision.narrative_coherence == 0.0
    assert result.provenance is not None
    assert result.provenance.narrative_coherence == 0.0
    assert result.provenance.causal_root_cast_id == "seed-root"
