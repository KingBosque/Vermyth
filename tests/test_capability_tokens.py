from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import pytest

from vermyth.adapters.a2a.gateway import TaskGateway
from vermyth.mcp.server import TOOL_DISPATCH
from vermyth.mcp.tools.facade import PermissionDenied


def _token_payload(*, scope: str, expiry: datetime, secret: str) -> dict:
    payload = {
        "holder": "agent-a",
        "tool_scope": scope,
        "expiry": expiry.isoformat(),
        "issuer": "issuer-a",
        "algorithm": "HMAC_SHA256",
    }
    material = "|".join(
        [
            payload["holder"],
            payload["tool_scope"],
            payload["expiry"],
            payload["issuer"],
            payload["algorithm"],
        ]
    ).encode("utf-8")
    payload["signature"] = hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()
    return payload


def test_vermyth_tools_scope_denied(make_tools):
    make_tools._allowed_tool_scope = ["query*"]
    try:
        make_tools.enforce_tool_scope("cast")
        raise AssertionError("expected scope denial")
    except PermissionDenied:
        pass


def test_a2a_capability_token_validation(make_tools, monkeypatch):
    monkeypatch.setenv("VERMYTH_REQUIRE_CAPABILITY_TOKENS", "1")
    monkeypatch.setenv("VERMYTH_CAPABILITY_SECRET", "secret")
    gateway = TaskGateway(tools=make_tools, tool_dispatch=TOOL_DISPATCH)
    token = _token_payload(
        scope="decide",
        expiry=datetime.now(timezone.utc) + timedelta(minutes=5),
        secret="secret",
    )
    out = gateway.execute_task(
        {
            "skill_id": "decide",
            "input": {
                "intent": {
                    "objective": "x",
                    "scope": "y",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "aspects": ["MIND"],
                "capability_token": token,
            },
        }
    )
    assert out["status"] == "completed"


def test_a2a_capability_token_scope_denied(make_tools, monkeypatch):
    monkeypatch.setenv("VERMYTH_REQUIRE_CAPABILITY_TOKENS", "1")
    monkeypatch.setenv("VERMYTH_CAPABILITY_SECRET", "secret")
    gateway = TaskGateway(tools=make_tools, tool_dispatch=TOOL_DISPATCH)
    token = _token_payload(
        scope="query*",
        expiry=datetime.now(timezone.utc) + timedelta(minutes=5),
        secret="secret",
    )
    out = gateway.execute_task(
        {
            "skill_id": "decide",
            "input": {
                "intent": {
                    "objective": "x",
                    "scope": "y",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "aspects": ["MIND"],
                "capability_token": token,
            },
        }
    )
    assert out["status"] == "failed"
    assert out["error"] == "capability_scope_denied"


def test_a2a_capability_token_expired(make_tools, monkeypatch):
    monkeypatch.setenv("VERMYTH_REQUIRE_CAPABILITY_TOKENS", "1")
    monkeypatch.setenv("VERMYTH_CAPABILITY_SECRET", "secret")
    gateway = TaskGateway(tools=make_tools, tool_dispatch=TOOL_DISPATCH)
    token = _token_payload(
        scope="decide",
        expiry=datetime.now(timezone.utc) - timedelta(minutes=1),
        secret="secret",
    )
    out = gateway.execute_task(
        {
            "skill_id": "decide",
            "input": {
                "intent": {
                    "objective": "x",
                    "scope": "y",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "aspects": ["MIND"],
                "capability_token": token,
            },
        }
    )
    assert out["status"] == "failed"
    assert "expired" in out["error"]


def test_capability_token_invalid_hmac_signature(make_tools, monkeypatch):
    monkeypatch.setenv("VERMYTH_REQUIRE_CAPABILITY_TOKENS", "1")
    monkeypatch.setenv("VERMYTH_CAPABILITY_SECRET", "secret")
    gateway = TaskGateway(tools=make_tools, tool_dispatch=TOOL_DISPATCH)
    token = _token_payload(
        scope="decide",
        expiry=datetime.now(timezone.utc) + timedelta(minutes=5),
        secret="secret",
    )
    token["signature"] = "0" * 64
    out = gateway.execute_task(
        {
            "skill_id": "decide",
            "input": {
                "intent": {
                    "objective": "x",
                    "scope": "y",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "aspects": ["MIND"],
                "capability_token": token,
            },
        }
    )
    assert out["status"] == "failed"
    assert "invalid capability token signature" in out["error"]


def test_capability_token_ed25519_round_trip(make_tools, monkeypatch):
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    monkeypatch.setenv("VERMYTH_REQUIRE_CAPABILITY_TOKENS", "1")
    monkeypatch.delenv("VERMYTH_CAPABILITY_SECRET", raising=False)
    monkeypatch.setenv("VERMYTH_CAPABILITY_ED25519_PUBLIC_KEY", public_pem)

    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "holder": "agent-a",
        "tool_scope": "decide",
        "expiry": expiry.isoformat(),
        "issuer": "issuer-a",
        "algorithm": "ED25519",
    }
    material = "|".join(
        [
            payload["holder"],
            payload["tool_scope"],
            payload["expiry"],
            payload["issuer"],
            payload["algorithm"],
        ]
    ).encode("utf-8")
    import base64

    sig = private_key.sign(material)
    payload["signature"] = base64.b64encode(sig).decode("ascii")

    gateway = TaskGateway(tools=make_tools, tool_dispatch=TOOL_DISPATCH)
    out = gateway.execute_task(
        {
            "skill_id": "decide",
            "input": {
                "intent": {
                    "objective": "x",
                    "scope": "y",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "aspects": ["MIND"],
                "capability_token": payload,
            },
        }
    )
    assert out["status"] == "completed"

