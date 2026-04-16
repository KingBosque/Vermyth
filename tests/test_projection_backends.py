import os

import pytest

from vermyth.engine.projection_backends import (
    EmbeddingBackend,
    FallbackProjectionBackend,
    LocalProjectionBackend,
    NullProjectionBackend,
    backend_from_env,
)
from vermyth.registry import AspectRegistry
from vermyth.schema import RegisteredAspect


def test_local_backend_returns_six_or_more_components():
    b = LocalProjectionBackend()
    out = b.project("remove the thing", "local workspace")
    assert isinstance(out, list)
    assert len(out) >= 6


def test_null_backend_returns_empty_list():
    b = NullProjectionBackend()
    assert b.project("x", "y") == []


def test_fallback_backend_uses_fallback_on_exception():
    class Boom(NullProjectionBackend):
        def project(self, objective: str, scope: str) -> list[float]:
            raise RuntimeError("boom")

    fb = FallbackProjectionBackend(Boom(), LocalProjectionBackend())
    out = fb.project("clarify", "scope")
    assert len(out) >= 6


def test_backend_from_env_none(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VERMYTH_BACKEND", "none")
    b = backend_from_env()
    assert b.project("x", "y") == []


def test_backend_from_env_local(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VERMYTH_BACKEND", "local")
    b = backend_from_env()
    out = b.project("build structure", "session")
    assert len(out) >= 6


def test_embedding_backend_returns_basis_dimension():
    def fake_embed(texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            seed = float((sum(ord(ch) for ch in text) % 7) + 1)
            out.append([seed, seed / 2.0, seed / 3.0, 1.0, 0.5, 0.25])
        return out

    b = EmbeddingBackend(embed_many=fake_embed)
    out = b.project("reveal signal", "workspace")
    assert len(out) >= 6


def test_embedding_backend_rebuilds_when_basis_changes():
    calls = {"n": 0}

    def fake_embed(texts: list[str]) -> list[list[float]]:
        calls["n"] += 1
        return [[1.0, 0.5, 0.25, 0.125, 0.0, 0.0] for _ in texts]

    b = EmbeddingBackend(embed_many=fake_embed)
    out1 = b.project("x", "y")
    registry = AspectRegistry.get()
    registry.register(
        RegisteredAspect(
            name="ECHO",
            polarity=1,
            entropy_coefficient=0.4,
            symbol="✧",
        )
    )
    out2 = b.project("x", "y")
    assert len(out2) == len(out1) + 1
    assert calls["n"] >= 3


def test_backend_from_env_auto_missing_key_falls_back_local(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VERMYTH_BACKEND", "auto")
    monkeypatch.setenv("VERMYTH_PROVIDER", "anthropic")
    monkeypatch.delenv("VERMYTH_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("VERMYTH_API_KEY", raising=False)
    monkeypatch.setenv("VERMYTH_FALLBACK", "local")
    b = backend_from_env()
    out = b.project("reveal signal", "workspace")
    assert len(out) >= 6


def test_backend_from_env_embed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VERMYTH_BACKEND", "embed")
    monkeypatch.setenv("VERMYTH_EMBED_MODEL", "all-MiniLM-L6-v2")
    b = backend_from_env()
    assert isinstance(b, EmbeddingBackend)


def test_backend_from_env_llm_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VERMYTH_BACKEND", "llm")
    monkeypatch.setenv("VERMYTH_PROVIDER", "anthropic")
    monkeypatch.delenv("VERMYTH_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("VERMYTH_API_KEY", raising=False)
    with pytest.raises(ValueError):
        backend_from_env()

