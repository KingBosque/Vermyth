import pytest

pytestmark = pytest.mark.experimental


def test_encode_decode_roundtrip():
    from vermyth.mcp.geometric import decode_packet, encode_packet, validate_proof
    from vermyth.schema import (
        Intent,
        ReversibilityClass,
        SemanticVector,
        SideEffectTolerance,
    )

    vec = SemanticVector(components=(0.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    intent = Intent(
        objective="study",
        scope="repo",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )
    packet = encode_packet(vec, intent)
    assert validate_proof(packet)

    vec2, intent2, lineage2 = decode_packet(packet)
    assert vec2.components[:6] == vec.components[:6]
    assert intent2.reversibility == ReversibilityClass.REVERSIBLE
    assert intent2.side_effect_tolerance == SideEffectTolerance.HIGH
    assert lineage2 is None


def test_proof_validation_detects_tamper():
    from vermyth.mcp.geometric import validate_proof
    from vermyth.schema import GeometricPacket

    payload = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0) + (0.0, 1.0, 0.0, 0.0) + (0.0, 0.0, 0.0, 0.0) + (0.0,)
    pkt = GeometricPacket(payload=payload, version=1)
    assert validate_proof(pkt)

    tampered = GeometricPacket(payload=payload[:-1] + (payload[-1] + 0.5,), version=1)
    assert not validate_proof(tampered)


def test_tool_geometric_cast_happy_path(make_tools):
    # Construct a minimal valid packet: aspect first4 dot intent4 == proof
    payload = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0] + [0.0, 1.0, 0.0, 0.0] + [0.0, 0.0, 0.0, 0.0]
    proof = payload[3] * payload[6]
    payload.append(proof)

    out = make_tools.tool_geometric_cast(payload=payload, branch_id="GEO_BRANCH")
    assert out["cast_id"]
    assert 0.0 <= float(out["resonance"]) <= 1.0

