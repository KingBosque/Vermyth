"""HTTP / A2A authentication abstraction (Bearer, dev token, optional JWT)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuthPrincipal:
    """Authenticated caller identity for audit and scope checks."""

    subject: str
    auth_method: str  # bearer_static | bearer_jwt | none
    scopes: frozenset[str]
    claims: dict[str, Any]


def parse_authorization_bearer(header_value: str | None) -> str | None:
    if not header_value:
        return None
    parts = header_value.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def resolve_principal(*, authorization: str | None) -> AuthPrincipal:
    """
    Production-style path: validate Bearer JWT when PyJWT + env are configured.
    Dev path: match VERMYTH_HTTP_TOKEN if set.
    """
    token = parse_authorization_bearer(authorization)
    if not token:
        return AuthPrincipal(subject="anonymous", auth_method="none", scopes=frozenset(), claims={})

    expected = os.environ.get("VERMYTH_HTTP_TOKEN")
    if expected and token == expected:
        scopes_raw = os.environ.get("VERMYTH_HTTP_SCOPES", "tool:*")
        scopes = frozenset(s.strip() for s in scopes_raw.split(",") if s.strip())
        return AuthPrincipal(
            subject="static-token",
            auth_method="bearer_static",
            scopes=scopes,
            claims={},
        )

    jwt_aud = os.environ.get("VERMYTH_JWT_AUDIENCE")
    jwt_iss = os.environ.get("VERMYTH_JWT_ISSUER")
    if jwt_aud and jwt_iss:
        try:
            import jwt
        except ImportError:
            raise ValueError(
                "JWT validation requested but PyJWT not installed: pip install -e .[auth-jwt]"
            ) from None
        algo = os.environ.get("VERMYTH_JWT_ALGORITHM", "HS256")
        secret = os.environ.get("VERMYTH_JWT_SECRET")
        if not secret:
            raise ValueError("VERMYTH_JWT_SECRET required for JWT validation")
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algo],
            audience=jwt_aud,
            issuer=jwt_iss,
        )
        sub = str(payload.get("sub", "jwt"))
        sc = payload.get("scope") or payload.get("scp") or "tool:*"
        if isinstance(sc, str):
            scopes = frozenset(x.strip() for x in sc.split() if x.strip())
        else:
            scopes = frozenset(str(x) for x in sc) if isinstance(sc, list) else frozenset({"tool:*"})
        return AuthPrincipal(
            subject=sub,
            auth_method="bearer_jwt",
            scopes=scopes,
            claims=dict(payload),
        )

    return AuthPrincipal(subject="unverified-bearer", auth_method="bearer_opaque", scopes=frozenset(), claims={})


def principal_allows_tool(principal: AuthPrincipal, tool_name: str) -> bool:
    if principal.auth_method == "none" and not os.environ.get("VERMYTH_HTTP_TOKEN"):
        return True
    for s in principal.scopes:
        if s == "tool:*" or s == f"tool:{tool_name}":
            return True
        if s.endswith("*") and tool_name.startswith(s[:-1]):
            return True
    return False
