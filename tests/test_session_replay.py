import pytest

pytestmark = pytest.mark.experimental


def test_session_checkpoint_rewind_fork(make_tools):
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
    cp = make_tools.session_checkpoint(sid)
    assert cp["sequence"] == 1

    make_tools.session_rewind_to(sid, 0)
    fork = make_tools.session_fork(sid, 0)
    assert fork["from_sequence"] == 0

