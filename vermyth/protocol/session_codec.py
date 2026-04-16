"""Session Codec V2: canonical serialization, hashing, and proofing.

This is designed to be reversible (lossless) at the payload level and to support
identity-oriented proof schemes without coupling trust into resonance math.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass

from vermyth.schema import (
    CanonicalPacketV2,
    CanonicalResponseV2,
    GossipPayload,
    NegotiatedCapabilities,
    PeerIdentity,
    ProofScheme,
)


def canonical_json_bytes(obj: object) -> bytes:
    # Deterministic JSON: sorted keys, no whitespace, UTF-8.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class SessionKeys:
    """Key material for SIGNED proof in v2.

    NOTE: This uses HMAC-SHA256 as a minimal signed proof. It is symmetric and
    should be treated as a placeholder until an asymmetric scheme is introduced.
    """

    key_id: str
    secret: bytes


def sign_hmac_sha256(secret: bytes, message: bytes) -> str:
    sig = hmac.new(secret, message, hashlib.sha256).digest()
    return base64.b64encode(sig).decode("ascii")


def verify_hmac_sha256(secret: bytes, message: bytes, signature_b64: str) -> bool:
    try:
        sig = base64.b64decode(signature_b64.encode("ascii"), validate=True)
    except Exception:
        return False
    expected = hmac.new(secret, message, hashlib.sha256).digest()
    return hmac.compare_digest(sig, expected)


def make_packet_payload_hash(payload: dict) -> str:
    return sha256_hex(canonical_json_bytes(payload))


def make_packet_proof(
    *,
    session_id: str,
    sequence: int,
    packet_type: str,
    payload_hash: str,
    scheme: ProofScheme,
    keys: SessionKeys | None,
) -> str:
    proof_input = canonical_json_bytes(
        {
            "session_id": session_id,
            "sequence": int(sequence),
            "packet_type": packet_type,
            "payload_hash": payload_hash,
        }
    )
    if scheme == ProofScheme.HASH:
        return sha256_hex(proof_input)
    if keys is None:
        raise ValueError("SIGNED proof requires SessionKeys")
    return sign_hmac_sha256(keys.secret, proof_input)


def verify_packet_proof(
    packet: CanonicalPacketV2,
    *,
    scheme: ProofScheme,
    keys: SessionKeys | None,
) -> bool:
    # Payload hash must match canonical bytes for identity-bound verification.
    try:
        payload_bytes = canonical_json_bytes(packet.payload)
    except Exception:
        return False
    if packet.payload_hash != sha256_hex(payload_bytes):
        return False
    proof_input = canonical_json_bytes(
        {
            "session_id": packet.session_id,
            "sequence": int(packet.sequence),
            "packet_type": packet.packet_type,
            "payload_hash": packet.payload_hash,
        }
    )
    if scheme == ProofScheme.HASH:
        return packet.proof == sha256_hex(proof_input)
    if keys is None:
        return False
    return verify_hmac_sha256(keys.secret, proof_input, packet.proof)


def encode_packet(
    *,
    session_id: str,
    sequence: int,
    packet_type: str,
    payload: dict,
    capabilities: NegotiatedCapabilities,
    keys: SessionKeys | None = None,
) -> CanonicalPacketV2:
    payload_hash = make_packet_payload_hash(payload)
    proof = make_packet_proof(
        session_id=session_id,
        sequence=sequence,
        packet_type=packet_type,
        payload_hash=payload_hash,
        scheme=capabilities.proof_scheme,
        keys=keys,
    )
    return CanonicalPacketV2(
        session_id=session_id,
        sequence=sequence,
        packet_type=packet_type,
        payload_hash=payload_hash,
        payload=payload,
        proof=proof,
    )


def encode_response(
    *,
    session_id: str,
    sequence: int,
    payload_hash: str,
    accepted: bool,
    capabilities: NegotiatedCapabilities,
    keys: SessionKeys | None = None,
) -> CanonicalResponseV2:
    proof_input = canonical_json_bytes(
        {
            "session_id": session_id,
            "sequence": int(sequence),
            "payload_hash": payload_hash,
            "accepted": bool(accepted),
        }
    )
    if capabilities.proof_scheme == ProofScheme.HASH:
        proof = sha256_hex(proof_input)
    else:
        if keys is None:
            raise ValueError("SIGNED response requires SessionKeys")
        proof = sign_hmac_sha256(keys.secret, proof_input)
    return CanonicalResponseV2(
        session_id=session_id,
        sequence=sequence,
        payload_hash=payload_hash,
        accepted=accepted,
        proof=proof,
    )


def verify_response(
    response: CanonicalResponseV2,
    *,
    accepted: bool,
    scheme: ProofScheme,
    keys: SessionKeys | None,
) -> bool:
    proof_input = canonical_json_bytes(
        {
            "session_id": response.session_id,
            "sequence": int(response.sequence),
            "payload_hash": response.payload_hash,
            "accepted": bool(accepted),
        }
    )
    if scheme == ProofScheme.HASH:
        return response.proof == sha256_hex(proof_input)
    if keys is None:
        return False
    return verify_hmac_sha256(keys.secret, proof_input, response.proof)


def default_identity(*, peer_id: str, key_id: str, scheme: ProofScheme) -> PeerIdentity:
    return PeerIdentity(peer_id=peer_id, key_id=key_id, scheme=scheme)


def federation_secret() -> bytes:
    return (os.environ.get("VERMYTH_FEDERATION_SECRET") or "").encode("utf-8")


def sign_gossip_payload(
    *,
    peer_id: str,
    key_id: str,
    seeds: list[dict],
    crystallized: list[dict],
    secret: bytes | None = None,
) -> str:
    s = secret if secret is not None else federation_secret()
    if not s:
        raise ValueError("VERMYTH_FEDERATION_SECRET not set")
    body = {
        "peer_id": peer_id,
        "key_id": key_id,
        "seeds": seeds,
        "crystallized": crystallized,
    }
    return hmac.new(s, canonical_json_bytes(body), hashlib.sha256).hexdigest()


def verify_gossip_payload(payload: GossipPayload) -> bool:
    s = federation_secret()
    if not s:
        return False
    body = {
        "peer_id": payload.peer_id,
        "key_id": payload.key_id,
        "seeds": payload.seeds,
        "crystallized": payload.crystallized,
    }
    expected = hmac.new(s, canonical_json_bytes(body), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, payload.proof)

