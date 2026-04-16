from __future__ import annotations

import os

import pytest

from vermyth.engine.projection_backends import EmbeddingBackend


@pytest.mark.skipif(
    os.environ.get("VERMYTH_EMBED_SMOKE") != "1",
    reason="set VERMYTH_EMBED_SMOKE=1 to run real embedding smoke test",
)
def test_embedding_backend_real_model_smoke() -> None:
    backend = EmbeddingBackend(model_name="all-MiniLM-L6-v2")
    out = backend.project("reveal hidden structure", "workspace")
    assert isinstance(out, list)
    assert len(out) >= 6
