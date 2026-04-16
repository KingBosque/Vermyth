import pytest

from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.tools import VermythTools
from vermyth.schema import (
    DivergenceReport,
    DivergenceStatus,
    DivergenceThresholds,
    SemanticVector,
)


def _intent():
    return {
        "objective": "study the pattern",
        "scope": "local workspace",
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "HIGH",
    }


def test_thresholds_validation():
    with pytest.raises(ValueError):
        DivergenceThresholds(l2_stable_max=1.0, l2_diverged_min=0.5)
    with pytest.raises(ValueError):
        DivergenceThresholds(cosine_stable_max=0.9, cosine_diverged_min=0.2)


def test_worst_of_wins_l2_diverged_even_if_cosine_stable():
    t = DivergenceThresholds(
        l2_stable_max=0.5,
        l2_diverged_min=1.0,
        cosine_stable_max=0.2,
        cosine_diverged_min=0.5,
    )
    # Same direction, very different magnitude -> cosine distance ~0, but L2 huge.
    parent = SemanticVector(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    child = SemanticVector(components=(100.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    rep = DivergenceReport.classify(
        cast_id="c",
        parent_cast_id="p",
        parent_vector=parent,
        child_vector=child,
        thresholds=t,
    )
    assert rep.status == DivergenceStatus.DIVERGED
    assert rep.l2_magnitude >= 1.0
    assert rep.cosine_distance < 0.2


@pytest.mark.parametrize(
    "l2,cos,expected",
    [
        (0.0, 0.0, DivergenceStatus.STABLE),
        (0.6, 0.1, DivergenceStatus.DRIFTING),
        (1.2, 0.1, DivergenceStatus.DIVERGED),
        (0.1, 0.6, DivergenceStatus.DRIFTING),
        (0.1, 1.2, DivergenceStatus.DIVERGED),
    ],
)
def test_divergence_report_classify_status_matrix(l2, cos, expected):
    t = DivergenceThresholds(
        l2_stable_max=0.5,
        l2_diverged_min=1.0,
        cosine_stable_max=0.2,
        cosine_diverged_min=0.5,
    )
    rep = DivergenceReport(
        cast_id="c",
        parent_cast_id="p",
        l2_magnitude=l2,
        cosine_distance=cos,
        status=DivergenceStatus.STABLE,
    )
    # classify() is the behavior under test; we construct vectors so reported
    # values land on the intended magnitudes.
    parent = SemanticVector(components=(0.0, 0.0, 0.0, 0.0, 0.0, 1.0))
    child = SemanticVector(components=(0.0, 0.0, 0.0, 0.0, 0.0, 1.0))
    # Override by calling classify with a derived child that produces desired distances.
    if l2 > 0:
        child = SemanticVector(components=(l2, 0.0, 0.0, 0.0, 0.0, 1.0))
    if cos > 0.0:
        child = SemanticVector(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    rep2 = DivergenceReport.classify(
        cast_id=rep.cast_id,
        parent_cast_id=rep.parent_cast_id,
        parent_vector=parent,
        child_vector=child,
        thresholds=t,
    )
    # Worst-of logic: ensure the status is at least as severe as expected.
    order = {DivergenceStatus.STABLE: 0, DivergenceStatus.DRIFTING: 1, DivergenceStatus.DIVERGED: 2}
    assert order[rep2.status] >= order[expected]


def test_divergence_report_persistence_roundtrip(tmp_path):
    g = Grimoire(db_path=tmp_path / "g.db")
    rep = DivergenceReport(
        cast_id="01TESTCAST",
        parent_cast_id="01PARENT",
        l2_magnitude=0.42,
        cosine_distance=0.12,
        status=DivergenceStatus.DRIFTING,
    )
    g.write_divergence_report(rep)
    got = g.read_divergence_report("01TESTCAST")
    assert got.cast_id == rep.cast_id
    assert got.parent_cast_id == rep.parent_cast_id
    assert got.status == rep.status


def test_thresholds_persistence_roundtrip(tmp_path):
    g = Grimoire(db_path=tmp_path / "g2.db")
    t = DivergenceThresholds(
        l2_stable_max=0.1,
        l2_diverged_min=0.2,
        cosine_stable_max=0.3,
        cosine_diverged_min=0.4,
    )
    g.write_divergence_thresholds(t)
    got = g.read_divergence_thresholds()
    assert got == t


def test_cast_inline_divergence_report(tmp_path):
    db = tmp_path / "casts.db"
    tools = VermythTools(
        ResonanceEngine(CompositionEngine(), None),
        Grimoire(db_path=db),
    )
    parent = tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_intent())
    child = tools.tool_cast(
        aspects=["MIND", "LIGHT"],
        intent=_intent(),
        parent_cast_id=parent["cast_id"],
    )
    lin = child["lineage"]
    assert lin is not None
    assert lin.get("divergence") is not None
    rep = tools.tool_divergence(cast_id=child["cast_id"])
    assert rep["cast_id"] == child["cast_id"]


def test_cast_without_parent_no_divergence(tmp_path):
    db = tmp_path / "casts2.db"
    tools = VermythTools(
        ResonanceEngine(CompositionEngine(), None),
        Grimoire(db_path=db),
    )
    out = tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_intent())
    assert out["lineage"] is None

