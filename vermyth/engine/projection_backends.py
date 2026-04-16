from __future__ import annotations

import json
import importlib
import math
import os
import re
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

from vermyth.contracts import ProjectionBackend
from vermyth.registry import AspectRegistry


def _clip(x: float) -> float:
    return max(-1.0, min(1.0, x))


def _normalize(components: Sequence[float]) -> list[float]:
    s = 0.0
    for c in components:
        s += c * c
    norm = math.sqrt(s)
    if norm == 0.0:
        return [0.0 for _ in components]
    return [float(c) / norm for c in components]


def _safe_stderr(message: str) -> None:
    try:
        os.write(2, (message + "\n").encode("utf-8", errors="replace"))
    except Exception:
        return


class ProjectionProvider(Protocol):
    def project(self, *, objective: str, scope: str) -> list[float]: ...


@dataclass(frozen=True)
class BackendConfig:
    """
    Backend configuration used by the factory.

    mode:
      - "none": always use NullProjectionBackend
      - "local": deterministic LocalProjectionBackend only
      - "llm": LLM backend only (no fallback unless fallback_mode enables it)
      - "auto": try LLM backend then fallback

    provider: provider identifier for LLM mode (e.g. "anthropic")
    api_key_env: env var name to read for provider API key
    model: provider model string
    timeout_s: best-effort request timeout
    fallback_mode:
      - "local": fall back to LocalProjectionBackend
      - "none": fall back to NullProjectionBackend (partial projection)
    """

    mode: str
    provider: str | None = None
    api_key_env: str | None = None
    model: str | None = None
    timeout_s: float = 10.0
    fallback_mode: str = "local"


class NullProjectionBackend(ProjectionBackend):
    """Explicit no-op backend. Returning an empty list forces partial projection upstream."""

    def project(self, objective: str, scope: str) -> list[float]:
        _ = objective, scope
        return []


class LocalProjectionBackend(ProjectionBackend):
    """
    Deterministic local backend: keyword heuristics into canonical aspect basis.

    Output length is always AspectRegistry.dimensionality (pads registered aspects with 0.0).
    """

    _ASPECT_KEYWORDS: dict[str, tuple[str, ...]] = {
        "VOID": ("delete", "remove", "erase", "null", "empty", "void", "silence"),
        "FORM": ("shape", "structure", "format", "schema", "organize", "compose", "build"),
        "MOTION": ("move", "flow", "shift", "change", "migrate", "iterate", "progress"),
        "MIND": ("think", "understand", "analyze", "reason", "learn", "explain", "decide"),
        "DECAY": ("decay", "break", "corrupt", "rot", "deprecate", "fade", "entropy"),
        "LIGHT": ("reveal", "clarify", "expose", "illuminate", "shine", "discover", "signal"),
    }

    def project(self, objective: str, scope: str) -> list[float]:
        text = f"{objective}\n{scope}".lower()
        dim = AspectRegistry.get().dimensionality
        base = [0.0 for _ in range(max(6, dim))]

        for i, canonical in enumerate(("VOID", "FORM", "MOTION", "MIND", "DECAY", "LIGHT")):
            kws = self._ASPECT_KEYWORDS.get(canonical, ())
            hits = 0
            for kw in kws:
                if kw in text:
                    hits += 1
            if hits:
                base[i] = _clip(0.25 * hits)

        base = _normalize(base)
        if dim > len(base):
            base.extend(0.0 for _ in range(dim - len(base)))
        return base[:dim]


class LLMProjectionBackend(ProjectionBackend):
    """
    LLM-backed projection. Provider supplies a 6+ float list in canonical aspect order.

    This backend is responsible for parsing and validation; it raises RuntimeError on
    provider/config failures so the fallback chain can take over.
    """

    def __init__(self, provider: ProjectionProvider) -> None:
        self._provider = provider

    def project(self, objective: str, scope: str) -> list[float]:
        out = self._provider.project(objective=objective, scope=scope)
        if not isinstance(out, list) or len(out) < 6:
            raise ValueError("projection provider returned invalid vector length")
        floats: list[float] = []
        for x in out:
            if not isinstance(x, (int, float)):
                raise ValueError("projection provider returned non-numeric component")
            xf = float(x)
            if xf < -1.0 or xf > 1.0:
                raise ValueError("projection provider returned component out of range")
            floats.append(xf)
        dim = AspectRegistry.get().dimensionality
        if len(floats) < dim:
            floats.extend(0.0 for _ in range(dim - len(floats)))
        return _normalize(floats)[:dim]


class FallbackProjectionBackend(ProjectionBackend):
    """Try primary backend; on any failure, fall back to secondary backend."""

    def __init__(self, primary: ProjectionBackend, fallback: ProjectionBackend) -> None:
        self._primary = primary
        self._fallback = fallback

    def project(self, objective: str, scope: str) -> list[float]:
        try:
            out = self._primary.project(objective, scope)
            if not isinstance(out, list) or len(out) < 6:
                raise ValueError("primary backend returned invalid vector")
            return out
        except Exception as exc:
            _safe_stderr(f"[vermyth] projection backend primary failed: {exc!r}")
            return self._fallback.project(objective, scope)


class AnthropicProvider(ProjectionProvider):
    """
    Anthropic provider implementation.

    Uses the `anthropic` SDK (declared dependency) and requests a strict JSON list.
    """

    def __init__(self, *, api_key: str, model: str, timeout_s: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_s = float(timeout_s)

    def project(self, *, objective: str, scope: str) -> list[float]:
        try:
            import anthropic  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"anthropic SDK unavailable: {exc!r}")

        client = anthropic.Anthropic(api_key=self._api_key)
        dim = AspectRegistry.get().dimensionality

        prompt = (
            "You are a projection function.\n"
            "Return ONLY a JSON array of floats.\n"
            "Order is: VOID, FORM, MOTION, MIND, DECAY, LIGHT.\n"
            "Each float must be in [-1.0, 1.0].\n"
            "Return at least 6 floats; you may return more.\n"
            f"Current dimensionality is {dim}; extra dimensions (beyond 6) should be 0.0.\n"
            "\n"
            f"objective: {objective}\n"
            f"scope: {scope}\n"
        )

        # SDK surfaces vary across versions; keep usage minimal and robust.
        msg = client.messages.create(
            model=self._model,
            max_tokens=128,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
            timeout=self._timeout_s,
        )

        text = ""
        try:
            # common shape: msg.content is list of blocks with .text
            blocks = getattr(msg, "content", None)
            if isinstance(blocks, list) and blocks:
                b0 = blocks[0]
                text = getattr(b0, "text", "") or ""
            else:
                text = getattr(msg, "completion", "") or ""
        except Exception:
            text = ""

        text = text.strip()
        if not text:
            raise RuntimeError("anthropic provider returned empty response")

        # Try strict JSON parse; fall back to extracting first bracketed list.
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\[[^\]]+\]", text, flags=re.S)
            if not m:
                raise ValueError("anthropic provider returned non-JSON output")
            parsed = json.loads(m.group(0))

        if not isinstance(parsed, list):
            raise ValueError("anthropic provider returned non-list JSON")
        return parsed


class EmbeddingBackend(ProjectionBackend):
    """
    Embedding-based projection backend.

    Computes an embedding for intent text and scores it against aspect reference
    embeddings. Rebuilds reference embeddings when basis dimensionality changes.
    """

    _CANONICAL_REFERENCES: dict[str, str] = {
        "VOID": "absence, removal, nullification, empty state",
        "FORM": "structure, schema, organization, shape and constraints",
        "MOTION": "movement, progress, transition, iteration and flow",
        "MIND": "reasoning, analysis, understanding, cognition and planning",
        "DECAY": "degradation, entropy, corruption, erosion and decline",
        "LIGHT": "clarity, revelation, signal, illumination and discovery",
    }

    def __init__(
        self,
        *,
        model_name: str = "all-MiniLM-L6-v2",
        embed_many: Callable[[list[str]], list[list[float]]] | None = None,
    ) -> None:
        self._model_name = model_name
        self._embed_many_override = embed_many
        self._model = None
        self._cached_basis_version: int | None = None
        self._aspect_reference_vectors: dict[str, list[float]] = {}

    def _embed_many(self, texts: list[str]) -> list[list[float]]:
        if self._embed_many_override is not None:
            out = self._embed_many_override(texts)
            return [[float(v) for v in vec] for vec in out]
        if self._model is None:
            try:
                st_module = importlib.import_module("sentence_transformers")
            except Exception as exc:
                raise RuntimeError(
                    "sentence-transformers is required for VERMYTH_BACKEND=embed"
                ) from exc
            self._model = st_module.SentenceTransformer(self._model_name)
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [[float(v) for v in vec] for vec in vectors]

    def _aspect_reference_text(self, aspect_name: str) -> str:
        base = self._CANONICAL_REFERENCES.get(
            aspect_name, f"{aspect_name} semantic intent axis"
        )
        return f"{aspect_name}: {base}"

    def _ensure_reference_vectors(self) -> None:
        current_basis = AspectRegistry.get().current_basis_version()
        if self._cached_basis_version == current_basis and self._aspect_reference_vectors:
            return
        aspects = AspectRegistry.get().full_order
        texts = [self._aspect_reference_text(a.name) for a in aspects]
        embeddings = self._embed_many(texts)
        if len(embeddings) != len(aspects):
            raise RuntimeError("embedding backend returned unexpected vector count")
        refs: dict[str, list[float]] = {}
        for aspect, emb in zip(aspects, embeddings):
            refs[aspect.name] = _normalize([float(x) for x in emb])
        self._aspect_reference_vectors = refs
        self._cached_basis_version = current_basis

    def project(self, objective: str, scope: str) -> list[float]:
        self._ensure_reference_vectors()
        dim = AspectRegistry.get().dimensionality
        query_text = f"{objective} // {scope}"
        query_vecs = self._embed_many([query_text])
        if not query_vecs:
            raise RuntimeError("embedding backend returned no query embedding")
        q = _normalize(query_vecs[0])
        out: list[float] = []
        for aspect in AspectRegistry.get().full_order:
            ref = self._aspect_reference_vectors.get(aspect.name)
            if ref is None:
                out.append(0.0)
                continue
            dot = 0.0
            d = max(len(q), len(ref))
            for i in range(d):
                a = q[i] if i < len(q) else 0.0
                b = ref[i] if i < len(ref) else 0.0
                dot += a * b
            out.append(_clip(dot))
        if len(out) < dim:
            out.extend(0.0 for _ in range(dim - len(out)))
        return _normalize(out[:dim])


def backend_from_env() -> ProjectionBackend:
    """
    Factory used by CLI + MCP. Controlled by env vars:

    - VERMYTH_BACKEND: none|local|embed|llm|auto (default: none)
    - VERMYTH_PROVIDER: provider id (default: anthropic)
    - VERMYTH_MODEL: provider model (default: claude-3-5-sonnet-latest)
    - VERMYTH_API_KEY / provider-specific key:
        - VERMYTH_ANTHROPIC_API_KEY (preferred for anthropic)
    - VERMYTH_FALLBACK: local|none (default: local when backend is auto)
    - VERMYTH_TIMEOUT_S: float seconds (default: 10)
    - VERMYTH_EMBED_MODEL: sentence-transformers model (default: all-MiniLM-L6-v2)
    """

    mode = (os.environ.get("VERMYTH_BACKEND") or "none").strip().lower()
    provider = (os.environ.get("VERMYTH_PROVIDER") or "anthropic").strip().lower()
    fallback_mode = (os.environ.get("VERMYTH_FALLBACK") or "local").strip().lower()
    model = (os.environ.get("VERMYTH_MODEL") or "claude-3-5-sonnet-latest").strip()
    embed_model = (os.environ.get("VERMYTH_EMBED_MODEL") or "all-MiniLM-L6-v2").strip()
    timeout_s = float(os.environ.get("VERMYTH_TIMEOUT_S") or "10")

    if mode not in {"none", "local", "embed", "llm", "auto"}:
        raise ValueError("VERMYTH_BACKEND must be one of: none, local, embed, llm, auto")
    if fallback_mode not in {"local", "none"}:
        raise ValueError("VERMYTH_FALLBACK must be one of: local, none")

    if mode == "none":
        return NullProjectionBackend()
    if mode == "local":
        return LocalProjectionBackend()
    if mode == "embed":
        return EmbeddingBackend(model_name=embed_model)

    if provider != "anthropic":
        raise ValueError(f"Unsupported provider: {provider!r}")

    api_key = (
        os.environ.get("VERMYTH_ANTHROPIC_API_KEY")
        or os.environ.get("VERMYTH_API_KEY")
        or ""
    ).strip()
    if not api_key:
        if mode == "llm":
            raise ValueError("Missing API key for LLM backend")
        # auto mode -> fall through to fallback selection
        llm_backend: ProjectionBackend = NullProjectionBackend()
    else:
        llm_backend = LLMProjectionBackend(
            AnthropicProvider(api_key=api_key, model=model, timeout_s=timeout_s)
        )

    if mode == "llm":
        return llm_backend

    fallback: ProjectionBackend
    if fallback_mode == "local":
        fallback = LocalProjectionBackend()
    else:
        fallback = NullProjectionBackend()
    return FallbackProjectionBackend(llm_backend, fallback)

