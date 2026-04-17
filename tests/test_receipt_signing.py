from __future__ import annotations

import pytest

from vermyth.receipt_signing import (
    receipt_canonical_bytes,
    sign_receipt_if_configured,
    verify_receipt_signature,
)
from vermyth.schema import ExecutionReceipt, NodeExecutionReceipt, NodeExecutionStatus, ProgramStatus


def _minimal_receipt() -> ExecutionReceipt:
    return ExecutionReceipt(
        execution_id="01HZEXAMPLEEXAMPLEEXAMPLE",
        program_id="01HZPROGEXAMPLEEXAMPLEEX",
        status=ProgramStatus.COMPLETED,
        nodes=[
            NodeExecutionReceipt(
                node_id="n1",
                status=NodeExecutionStatus.OK,
            )
        ],
        signature=None,
        signing_key_id=None,
    )


def test_receipt_canonical_stable():
    r = _minimal_receipt()
    a = receipt_canonical_bytes(r)
    b = receipt_canonical_bytes(r)
    assert a == b


def test_sign_and_verify_round_trip(monkeypatch):
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    monkeypatch.setenv("VERMYTH_RECEIPT_SIGNING_KEY", priv_pem)
    monkeypatch.setenv("VERMYTH_RECEIPT_SIGNING_KEY_ID", "test-key")
    r = sign_receipt_if_configured(_minimal_receipt())
    assert r.signature
    assert verify_receipt_signature(r, public_pem=pub_pem) is True
