"""Canonical serialization and optional Ed25519 signing for execution receipts."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from vermyth.schema import ExecutionReceipt


def receipt_canonical_dict(receipt: ExecutionReceipt) -> dict[str, Any]:
    """Stable dict for signing (excludes signature fields)."""
    payload = receipt.model_dump(mode="json")
    for k in ("signature", "signing_key_id"):
        payload.pop(k, None)
    return payload


def receipt_canonical_bytes(receipt: ExecutionReceipt) -> bytes:
    return json.dumps(
        receipt_canonical_dict(receipt),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sign_receipt_if_configured(receipt: ExecutionReceipt) -> ExecutionReceipt:
    """When VERMYTH_RECEIPT_SIGNING_KEY (PEM Ed25519 private) is set, sign canonical bytes."""
    pem = os.environ.get("VERMYTH_RECEIPT_SIGNING_KEY")
    key_id = os.environ.get("VERMYTH_RECEIPT_SIGNING_KEY_ID", "default")
    if not pem:
        return receipt
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise ImportError("pip install -e .[a2a-crypto] for receipt signing") from exc

    key = serialization.load_pem_private_key(pem.strip().encode(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("VERMYTH_RECEIPT_SIGNING_KEY must be an Ed25519 private key PEM")
    sig = key.sign(receipt_canonical_bytes(receipt))
    b64 = base64.b64encode(sig).decode("ascii")
    return receipt.model_copy(update={"signature": b64, "signing_key_id": key_id})


def verify_receipt_signature(receipt: ExecutionReceipt, *, public_pem: str) -> bool:
    """Verify Ed25519 signature using PEM public key."""
    if not receipt.signature:
        return False
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
    except ImportError as exc:
        raise ImportError("pip install -e .[a2a-crypto] for receipt verification") from exc

    pub = serialization.load_pem_public_key(public_pem.strip().encode())
    if not isinstance(pub, Ed25519PublicKey):
        raise ValueError("public key must be Ed25519")
    sig = base64.b64decode(receipt.signature, validate=True)
    try:
        pub.verify(sig, receipt_canonical_bytes(receipt))
    except InvalidSignature:
        return False
    return True
