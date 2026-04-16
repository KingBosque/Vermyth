import pytest

pytestmark = pytest.mark.experimental


def test_session_codec_packet_roundtrip_signed(tmp_path):
    from pathlib import Path

    from vermyth.grimoire.store import Grimoire
    from vermyth.protocol.session_codec import SessionKeys, encode_packet, verify_packet_proof
    from vermyth.schema import NegotiatedCapabilities, PeerIdentity, ProofScheme, SessionRecord, SessionTransport

    g = Grimoire(db_path=Path(tmp_path) / "s.db")
    caps = NegotiatedCapabilities(codec_version=2, aspect_dimensionality=6, proof_scheme=ProofScheme.SIGNED)
    keys = SessionKeys(key_id="k1", secret=b"secret")

    # Packets are FK-bound to sessions.
    g.write_session(
        SessionRecord(
            session_id="S",
            transport=SessionTransport.JSONRPC,
            local_identity=PeerIdentity(peer_id="A", key_id="k1", scheme=ProofScheme.SIGNED),
            remote_identity=PeerIdentity(peer_id="B", key_id="k2", scheme=ProofScheme.SIGNED),
            capabilities=caps,
        )
    )

    payload = {"aspects": ["MIND"], "intent": {"objective": "x", "scope": "y", "reversibility": "REVERSIBLE", "side_effect_tolerance": "HIGH"}}
    pkt = encode_packet(session_id="S", sequence=1, packet_type="cast", payload=payload, capabilities=caps, keys=keys)

    assert verify_packet_proof(pkt, scheme=caps.proof_scheme, keys=keys)
    g.write_session_packet(pkt)
    rows = g.query_session_packets("S", limit=10)
    assert rows[0].payload == payload


def test_session_replay_guard(make_tools):
    sid = make_tools.session_open(
        transport="JSONRPC",
        local_peer_id="A",
        local_key_id="k",
        remote_peer_id="B",
        remote_key_id="k2",
        signing_secret=b"secret",
    )["session_id"]

    pkt1 = make_tools.session_encode_packet(
        session_id=sid,
        sequence=1,
        packet_type="cast",
        payload={"aspects": ["MIND"], "intent": {"objective": "x", "scope": "y", "reversibility": "REVERSIBLE", "side_effect_tolerance": "HIGH"}},
    )
    make_tools.session_apply_packet(pkt1)

    # Replaying same sequence should fail.
    try:
        make_tools.session_apply_packet(pkt1)
        assert False, "expected replay error"
    except ValueError:
        pass

