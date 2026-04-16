from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.protocol.session_codec import (
    SessionKeys,
    encode_packet as encode_session_packet,
    encode_response as encode_session_response,
    verify_packet_proof,
)
from vermyth.schema import (
    CanonicalPacketV2,
    NegotiatedCapabilities,
    PeerIdentity,
    SessionRecord,
    SessionStatus,
    SessionTransport,
)

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools


def session_open(
    tools: "VermythTools",
    *,
    transport: str,
    local_peer_id: str,
    local_key_id: str,
    remote_peer_id: str,
    remote_key_id: str,
    codec_version: int = 2,
    proof_scheme: str = "SIGNED",
    aspect_dimensionality: int = 6,
    max_packet_bytes: int | None = None,
    channel_branch_id: str | None = None,
    anchor_cast_id: str | None = None,
    signing_secret: bytes | None = None,
) -> dict[str, Any]:
    caps = NegotiatedCapabilities(
        codec_version=int(codec_version),
        aspect_dimensionality=int(aspect_dimensionality),
        proof_scheme=proof_scheme,
        supports_binary=(transport == "BINARY"),
        supports_replay_guard=True,
        max_packet_bytes=max_packet_bytes,
    )
    local = PeerIdentity(peer_id=local_peer_id, key_id=local_key_id, scheme=caps.proof_scheme)
    remote = PeerIdentity(peer_id=remote_peer_id, key_id=remote_key_id, scheme=caps.proof_scheme)
    record = SessionRecord(
        transport=SessionTransport[str(transport)],
        local_identity=local,
        remote_identity=remote,
        capabilities=caps,
        status=SessionStatus.OPEN,
        anchor_cast_id=anchor_cast_id,
        channel_branch_id=channel_branch_id,
    )
    tools._grimoire.write_session(record)
    if signing_secret is not None:
        tools._session_key_cache = getattr(tools, "_session_key_cache", {})
        tools._session_key_cache[record.session_id] = SessionKeys(
            key_id=local_key_id, secret=signing_secret
        )
    return {"session_id": record.session_id, "capabilities": record.capabilities.model_dump()}


def session_apply_packet(tools: "VermythTools", packet_dict: dict[str, Any]) -> dict[str, Any]:
    packet = CanonicalPacketV2.model_validate(packet_dict)
    session = tools._grimoire.read_session(packet.session_id)
    if packet.sequence <= session.last_sequence:
        raise ValueError("replay detected: sequence not increasing")
    keys = None
    if session.capabilities.proof_scheme == session.capabilities.proof_scheme.SIGNED:
        cache = getattr(tools, "_session_key_cache", {})
        keys = cache.get(packet.session_id)
    if not verify_packet_proof(packet, scheme=session.capabilities.proof_scheme, keys=keys):
        raise ValueError("invalid packet proof")
    tools._grimoire.write_session_packet(packet)
    tools._grimoire.advance_session_sequence(packet.session_id, int(packet.sequence))

    accepted = True
    result_payload: dict[str, Any] = {}
    packet_type = packet.packet_type
    payload = packet.payload
    binary_handler = BINARY_DISPATCH.get(packet_type)
    if binary_handler is None:
        accepted = False
        result_payload = {"error": f"unknown packet_type: {packet_type}"}
    else:
        result_payload = binary_handler(tools, payload)

    keys = None
    if session.capabilities.proof_scheme == session.capabilities.proof_scheme.SIGNED:
        cache = getattr(tools, "_session_key_cache", {})
        keys = cache.get(packet.session_id)
    resp = encode_session_response(
        session_id=packet.session_id,
        sequence=int(packet.sequence),
        payload_hash=packet.payload_hash,
        accepted=accepted,
        capabilities=session.capabilities,
        keys=keys,
    )
    tools._grimoire.write_session_response(resp)
    return {"accepted": accepted, "result": result_payload, "response": resp.model_dump()}


def session_checkpoint(tools: "VermythTools", session_id: str) -> dict[str, Any]:
    session = tools._grimoire.read_session(session_id)
    return {"session_id": session.session_id, "sequence": int(session.last_sequence)}


def session_rewind_to(tools: "VermythTools", session_id: str, sequence: int) -> dict[str, Any]:
    session = tools._grimoire.read_session(session_id)
    if int(sequence) < 0 or int(sequence) > int(session.last_sequence):
        raise ValueError("invalid rewind sequence")
    rewound = SessionRecord.model_construct(
        session_id=session.session_id,
        opened_at=session.opened_at,
        closed_at=session.closed_at,
        status=session.status,
        transport=session.transport,
        local_identity=session.local_identity,
        remote_identity=session.remote_identity,
        capabilities=session.capabilities,
        last_sequence=int(sequence),
        anchor_cast_id=session.anchor_cast_id,
        channel_branch_id=session.channel_branch_id,
    )
    tools._grimoire.write_session(rewound)
    return {"session_id": session_id, "rewound_to": int(sequence)}


def session_replay_from(
    tools: "VermythTools", session_id: str, sequence: int, *, limit: int = 100
) -> dict[str, Any]:
    packets = tools._grimoire.query_session_packets(session_id, limit=int(limit))
    out: list[dict[str, Any]] = []
    for packet in packets:
        if int(packet.sequence) <= int(sequence):
            continue
        out.append(session_apply_packet(tools, packet.model_dump()))
    return {"session_id": session_id, "replayed": len(out), "results": out}


def session_fork(
    tools: "VermythTools",
    session_id: str,
    from_sequence: int,
    *,
    new_transport: str | None = None,
) -> dict[str, Any]:
    base = tools._grimoire.read_session(session_id)
    if int(from_sequence) < 0 or int(from_sequence) > int(base.last_sequence):
        raise ValueError("invalid fork sequence")
    forked = SessionRecord(
        transport=base.transport if new_transport is None else SessionTransport[str(new_transport)],
        local_identity=base.local_identity,
        remote_identity=base.remote_identity,
        capabilities=base.capabilities,
        status=SessionStatus.OPEN,
        anchor_cast_id=base.anchor_cast_id,
        channel_branch_id=base.channel_branch_id,
        last_sequence=int(from_sequence),
    )
    tools._grimoire.write_session(forked)
    return {"forked_session_id": forked.session_id, "from_sequence": int(from_sequence)}


def session_encode_packet(
    tools: "VermythTools",
    *,
    session_id: str,
    sequence: int,
    packet_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    session = tools._grimoire.read_session(session_id)
    keys = None
    if session.capabilities.proof_scheme == session.capabilities.proof_scheme.SIGNED:
        cache = getattr(tools, "_session_key_cache", {})
        keys = cache.get(session_id)
    packet = encode_session_packet(
        session_id=session_id,
        sequence=int(sequence),
        packet_type=str(packet_type),
        payload=payload,
        capabilities=session.capabilities,
        keys=keys,
    )
    return packet.model_dump()


def _binary_cast(tools: "VermythTools", payload: dict[str, Any]) -> dict[str, Any]:
    return tools.tool_cast(
        aspects=payload.get("aspects", []),
        intent=payload.get("intent", {}),
        parent_cast_id=payload.get("parent_cast_id"),
        branch_id=payload.get("branch_id"),
        chained=bool(payload.get("chained", False)),
        force=bool(payload.get("force", False)),
    )


def _binary_fluid_cast(tools: "VermythTools", payload: dict[str, Any]) -> dict[str, Any]:
    return tools.tool_fluid_cast(
        vector=payload.get("vector", []),
        intent=payload.get("intent", {}),
        parent_cast_id=payload.get("parent_cast_id"),
        branch_id=payload.get("branch_id"),
    )


def _binary_geometric_cast(tools: "VermythTools", payload: dict[str, Any]) -> dict[str, Any]:
    return tools.tool_geometric_cast(
        payload=payload.get("payload", []),
        version=int(payload.get("version", 1)),
        branch_id=payload.get("branch_id"),
        force=bool(payload.get("force", False)),
    )


BINARY_DISPATCH = {
    "cast": _binary_cast,
    "fluid_cast": _binary_fluid_cast,
    "geometric_cast": _binary_geometric_cast,
}
