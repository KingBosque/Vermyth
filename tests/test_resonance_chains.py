import pytest


def _mk_intent(*, rev: str, tol: str) -> dict:
    return {
        "objective": "chain test",
        "scope": "unit",
        "reversibility": rev,
        "side_effect_tolerance": tol,
    }


def test_chained_cast_rejects_decoherent_without_force(resonance_engine, composition_engine):
    from vermyth.engine.resonance import ChannelDecoherentError
    from vermyth.schema import (
        AspectID,
        ChannelState,
        ChannelStatus,
        Intent,
        ReversibilityClass,
        SemanticVector,
        SideEffectTolerance,
        VerdictType,
    )

    aspects = frozenset({AspectID.MIND})
    intent = Intent(
        objective="x",
        scope="y",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )

    decoherent = ChannelState(
        branch_id="B",
        cast_count=10,
        cumulative_resonance=0.0,
        mean_resonance=0.0,
        coherence_streak=0,
        last_verdict_type=VerdictType.INCOHERENT,
        status=ChannelStatus.DECOHERENT,
        last_cast_id="C",
        constraint_vector=SemanticVector(components=(0, 0, 0, 0, 0, 0)),
    )

    with pytest.raises(ChannelDecoherentError):
        resonance_engine.chained_cast(aspects, intent, decoherent, force=False)

    # Force should allow cast.
    result, state = resonance_engine.chained_cast(aspects, intent, decoherent, force=True)
    assert result.cast_id
    assert state.branch_id == "B"


def test_chained_cast_blends_constraint_changes_resonance(resonance_engine):
    from vermyth.schema import (
        AspectID,
        ChannelState,
        ChannelStatus,
        Intent,
        ReversibilityClass,
        SemanticVector,
        SideEffectTolerance,
        VerdictType,
    )

    aspects = frozenset({AspectID.MIND})
    intent = Intent(
        objective="x",
        scope="y",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )
    base = resonance_engine.cast(aspects, intent)

    # Push the intent vector away from the sigil by applying an opposing constraint.
    opposing = SemanticVector(components=(0.0, 0.0, 0.0, -1.0, 0.0, 0.0))
    channel = ChannelState(
        branch_id="B2",
        cast_count=0,
        cumulative_resonance=0.0,
        mean_resonance=1.0,
        coherence_streak=0,
        last_verdict_type=VerdictType.COHERENT,
        status=ChannelStatus.COHERENT,
        last_cast_id="ROOT",
        constraint_vector=opposing,
    )
    chained, _state = resonance_engine.chained_cast(aspects, intent, channel)
    assert float(chained.verdict.resonance.adjusted) != float(base.verdict.resonance.adjusted)


def test_sync_channel_resets_status(resonance_engine):
    from vermyth.schema import (
        ChannelState,
        ChannelStatus,
        SemanticVector,
        VerdictType,
    )

    state = ChannelState(
        branch_id="B3",
        cast_count=5,
        cumulative_resonance=1.0,
        mean_resonance=0.2,
        coherence_streak=0,
        last_verdict_type=VerdictType.PARTIAL,
        status=ChannelStatus.DECOHERENT,
        last_cast_id="C",
        constraint_vector=SemanticVector(components=(0, 0, 0, 0, 0, 0)),
    )
    synced = resonance_engine.sync_channel(state, seeds=[])
    assert synced.status == ChannelStatus.COHERENT
    assert synced.coherence_streak == 0


def test_tools_channel_state_roundtrip(make_tools, valid_intent):
    # Create a channel via chained cast and then read it back.
    out = make_tools.tool_cast(
        aspects=["MIND"],
        intent=valid_intent,
        branch_id="BRANCH_X",
        chained=True,
    )
    assert out["cast_id"]
    state = make_tools.tool_channel_status("BRANCH_X")
    assert state["branch_id"] == "BRANCH_X"
    assert state["cast_count"] >= 1

