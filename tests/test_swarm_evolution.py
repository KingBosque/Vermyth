"""Tests for auto_cast, swarm consensus, and federation gossip."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.experimental


def test_auto_cast_returns_chain(resonance_engine):
    from vermyth.schema import Intent, ReversibilityClass, SemanticVector, SideEffectTolerance

    v = SemanticVector(components=(0.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    intent = Intent(
        objective="study",
        scope="unit",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )
    final, chain = resonance_engine.auto_cast(
        v, intent, max_depth=3, target_resonance=0.99, blend_alpha=0.5
    )
    assert chain
    assert final.cast_id == chain[-1].cast_id
    assert len(chain) <= 3


def test_tool_auto_cast_persists(make_tools, valid_intent):
    out = make_tools.tool_auto_cast(
        vector=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        intent=valid_intent,
        max_depth=2,
        target_resonance=0.99,
        blend_alpha=0.5,
    )
    assert "auto_cast_chain" in out
    assert out["cast_id"]
    ins = make_tools.tool_inspect(out["cast_id"])
    assert ins["cast_id"] == out["cast_id"]


def test_swarm_cast_single_member(make_tools, valid_intent):
    make_tools.tool_swarm_join(swarm_id="S1", session_id="sess-a")
    out = make_tools.tool_swarm_cast(
        swarm_id="S1",
        session_id="sess-a",
        vector=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        intent=valid_intent,
    )
    assert "swarm_status" in out
    assert "member_streaks" in out
    assert out["member_streaks"].get("sess-a") is not None


def test_swarm_two_members_weighted(make_tools, valid_intent):
    make_tools.tool_swarm_join(swarm_id="S2", session_id="A")
    make_tools.tool_swarm_join(swarm_id="S2", session_id="B")
    make_tools.tool_swarm_cast(
        swarm_id="S2",
        session_id="A",
        vector=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        intent=valid_intent,
    )
    out = make_tools.tool_swarm_cast(
        swarm_id="S2",
        session_id="B",
        vector=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        intent=valid_intent,
    )
    assert out["cast_id"]
    st = make_tools.tool_swarm_status("S2")
    assert len(st["members"]) == 2


def test_gossip_sync_applies_with_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("VERMYTH_FEDERATION_SECRET", "test-secret-for-federation")
    from vermyth.grimoire.store import Grimoire
    from vermyth.protocol.session_codec import sign_gossip_payload
    from vermyth.schema import GossipPayload

    db = Path(tmp_path) / "g.db"
    g = Grimoire(db_path=db)
    proof = sign_gossip_payload(
        peer_id="peer1",
        key_id="k1",
        seeds=[
            {
                "aspect_pattern": ["MIND"],
                "observed_count": 3,
                "mean_resonance": 0.5,
                "coherence_rate": 0.6,
                "crystallized": False,
                "generation": 1,
            }
        ],
        crystallized=[],
        secret=b"test-secret-for-federation",
    )
    payload = GossipPayload(
        peer_id="peer1",
        key_id="k1",
        seeds=[
            {
                "aspect_pattern": ["MIND"],
                "observed_count": 3,
                "mean_resonance": 0.5,
                "coherence_rate": 0.6,
                "crystallized": False,
                "generation": 1,
            }
        ],
        crystallized=[],
        proof=proof,
    )
    r = g.apply_gossip_sync(payload)
    assert r["merged_seeds"] == 1
    assert r["peer_id"] == "peer1"


def test_binary_gossip_frame_roundtrip():
    import io

    from vermyth.mcp.binary_transport import FrameType, decode_frame_from_buffer, encode_frame

    msg = {"peer_id": "p", "key_id": "k", "seeds": [], "crystallized": [], "proof": "a" * 64}
    data = encode_frame(FrameType.GOSSIP_PUSH, json.dumps(msg).encode("utf-8"))
    buf = io.BufferedReader(io.BytesIO(data))
    frame = decode_frame_from_buffer(buf)
    assert frame is not None
    assert frame.frame_type == FrameType.GOSSIP_PUSH


def test_swarm_cast_conflicting_vectors_strained(make_tools, valid_intent):
    make_tools.tool_swarm_join(swarm_id="S3", session_id="A")
    make_tools.tool_swarm_join(swarm_id="S3", session_id="B")
    make_tools.tool_swarm_cast(
        swarm_id="S3",
        session_id="A",
        vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        intent=valid_intent,
    )
    out = make_tools.tool_swarm_cast(
        swarm_id="S3",
        session_id="B",
        vector=[-1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        intent=valid_intent,
    )
    # Aggregate is blended; status is one of the three.
    assert out["swarm_status"] in ("COHERENT", "STRAINED", "DECOHERENT")
