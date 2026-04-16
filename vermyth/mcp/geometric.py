"""Geometric protocol helpers (vector-encoded packets and responses).

V1 geometric packets remain a compatibility layer; lossy intent reconstruction
is intentional. Use Session Codec V2 and `vermyth.protocol.session_codec` for
non-lossy semantics.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from vermyth.schema import (
    GeometricPacket,
    GeometricResponse,
    Intent,
    Lineage,
    ReversibilityClass,
    SemanticVector,
    SideEffectTolerance,
)


def _hash4(text: str) -> tuple[float, float, float, float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # Map 4 bytes into [-1, 1]
    out: list[float] = []
    for i in range(4):
        b = h[i]
        out.append((float(b) / 255.0) * 2.0 - 1.0)
    return (out[0], out[1], out[2], out[3])


def encode_packet(
    aspects_or_vector: SemanticVector,
    intent: Intent,
    lineage: Lineage | None = None,
    *,
    version: int = 1,
) -> GeometricPacket:
    # v1 uses 6 aspect dims + 4 intent dims + 4 lineage dims + proof.
    a = tuple(float(x) for x in aspects_or_vector.components[:6])
    if len(a) < 6:
        a = a + tuple(0.0 for _ in range(6 - len(a)))

    rev_map = {
        ReversibilityClass.REVERSIBLE: -1.0,
        ReversibilityClass.PARTIAL: 0.0,
        ReversibilityClass.IRREVERSIBLE: 1.0,
    }
    tol_map = {
        SideEffectTolerance.NONE: 0.0,
        SideEffectTolerance.LOW: 0.33,
        SideEffectTolerance.MEDIUM: 0.66,
        SideEffectTolerance.HIGH: 1.0,
    }
    intent4 = (
        float(rev_map[intent.reversibility]),
        float(tol_map[intent.side_effect_tolerance]),
        min(1.0, max(0.0, len(intent.scope) / 200.0)),
        min(1.0, max(0.0, len(intent.objective) / 500.0)),
    )
    lineage4 = (0.0, 0.0, 0.0, 0.0) if lineage is None else _hash4(lineage.parent_cast_id)

    proof = a[0] * intent4[0] + a[1] * intent4[1] + a[2] * intent4[2] + a[3] * intent4[3]
    payload = a + intent4 + lineage4 + (float(proof),)
    return GeometricPacket(payload=payload, version=version)


def decode_packet(packet: GeometricPacket) -> tuple[SemanticVector, Intent, Lineage | None]:
    # This is intentionally lossy in v1: it reconstructs only enum-like fields.
    vec = packet.aspect_vector()
    i0, i1, _i2, _i3 = packet.intent_encoding()

    reversibility: ReversibilityClass
    if i0 <= -0.5:
        reversibility = ReversibilityClass.REVERSIBLE
    elif i0 >= 0.5:
        reversibility = ReversibilityClass.IRREVERSIBLE
    else:
        reversibility = ReversibilityClass.PARTIAL

    tolerance: SideEffectTolerance
    if i1 <= 0.20:
        tolerance = SideEffectTolerance.NONE
    elif i1 <= 0.50:
        tolerance = SideEffectTolerance.LOW
    elif i1 <= 0.85:
        tolerance = SideEffectTolerance.MEDIUM
    else:
        tolerance = SideEffectTolerance.HIGH

    intent = Intent(
        objective="geometric_packet",
        scope="geometric_packet",
        reversibility=reversibility,
        side_effect_tolerance=tolerance,
    )

    lineage_hash = packet.lineage_hash()
    lineage = None
    if any(abs(float(x)) > 1e-12 for x in lineage_hash):
        # Cannot recover parent id from hash; preserve a placeholder.
        lineage = Lineage(parent_cast_id="HASHED_PARENT", depth=1, branch_id=None)  # type: ignore[arg-type]

    return vec, intent, lineage


def validate_proof(packet: GeometricPacket, *, epsilon: float = 1e-4) -> bool:
    return packet.validate_proof(epsilon=epsilon)


def encode_response(
    *,
    verdict_vector: SemanticVector,
    resonance: float,
    channel_delta: Optional[SemanticVector] = None,
) -> GeometricResponse:
    proof = float(verdict_vector.components[0] if verdict_vector.components else 0.0) * float(resonance)
    return GeometricResponse(
        verdict_vector=verdict_vector,
        resonance=float(resonance),
        channel_delta=channel_delta,
        proof_hash=proof,
    )

