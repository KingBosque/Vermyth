from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone

from vermyth.schema import CapabilityToken


def _sign_material(token: CapabilityToken) -> bytes:
    material = "|".join(
        [
            token.holder,
            token.tool_scope,
            token.expiry.isoformat(),
            token.issuer,
            token.algorithm,
        ]
    )
    return material.encode("utf-8")


def _verify_hmac(token: CapabilityToken, *, shared_secret: str) -> CapabilityToken:
    expected = hmac.new(
        shared_secret.encode("utf-8"),
        _sign_material(token),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, token.signature):
        raise ValueError("invalid capability token signature")
    return token


def _verify_ed25519(token: CapabilityToken, *, public_key_pem: str) -> CapabilityToken:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise ValueError(
            "Ed25519 verification requires optional dependency: pip install -e .[a2a-crypto]"
        ) from exc

    key = serialization.load_pem_public_key(public_key_pem.strip().encode())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("VERMYTH_CAPABILITY_ED25519_PUBLIC_KEY must be an Ed25519 public key")
    try:
        sig = base64.b64decode(token.signature, validate=True)
    except Exception as exc:
        raise ValueError("invalid capability token signature encoding") from exc
    try:
        key.verify(sig, _sign_material(token))
    except InvalidSignature:
        raise ValueError("invalid capability token signature")
    return token


def verify_capability_token(token_payload: dict, *, shared_secret: str | None) -> CapabilityToken:
    """
    Verify a capability token.

    - ``algorithm=HMAC_SHA256``: HMAC-SHA256 over :func:`_sign_material` using ``VERMYTH_CAPABILITY_SECRET``.
    - ``algorithm=ED25519``: if ``VERMYTH_CAPABILITY_ED25519_PUBLIC_KEY`` is set (PEM), verify a **base64**
      Ed25519 signature over the same material. Otherwise, if ``shared_secret`` is set, fall back to
      HMAC (development / transitional).
    """
    token = CapabilityToken.model_validate(token_payload)
    if token.expiry < datetime.now(timezone.utc):
        raise ValueError("capability token expired")

    algo = (token.algorithm or "").upper().replace("-", "_")
    pub = os.environ.get("VERMYTH_CAPABILITY_ED25519_PUBLIC_KEY")

    if algo in ("HMAC_SHA256", "HMACSHA256"):
        if shared_secret is None:
            raise ValueError("capability secret is not configured")
        return _verify_hmac(token, shared_secret=shared_secret)

    if algo in ("ED25519", "ED25519V1"):
        if pub:
            return _verify_ed25519(token, public_key_pem=pub)
        if shared_secret is not None:
            return _verify_hmac(token, shared_secret=shared_secret)
        raise ValueError(
            "Ed25519 tokens require VERMYTH_CAPABILITY_ED25519_PUBLIC_KEY "
            "or VERMYTH_CAPABILITY_SECRET for HMAC fallback"
        )

    raise ValueError(f"unsupported capability algorithm: {token.algorithm}")
