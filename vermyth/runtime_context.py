"""Request-scoped context (correlation ids, principal audit) for HTTP/MCP/A2A."""

from __future__ import annotations

import contextvars

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "vermyth_correlation_id", default=None
)
_principal_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "vermyth_principal_id", default=None
)


def set_correlation_id(value: str | None) -> contextvars.Token[str | None]:
    return _correlation_id.set(value)


def reset_correlation_id(token: contextvars.Token[str | None]) -> None:
    _correlation_id.reset(token)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_principal_id(value: str | None) -> contextvars.Token[str | None]:
    return _principal_id.set(value)


def reset_principal_id(token: contextvars.Token[str | None]) -> None:
    _principal_id.reset(token)


def get_principal_id() -> str | None:
    return _principal_id.get()
