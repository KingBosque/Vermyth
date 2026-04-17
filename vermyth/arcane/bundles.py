"""Load and resolve built-in semantic bundles from package data."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from vermyth.arcane.types import SemanticBundleManifest


def _bundles_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "arcane" / "bundles"


@lru_cache(maxsize=32)
def load_bundle(bundle_id: str, version: int) -> SemanticBundleManifest:
    path = _bundles_dir() / f"{bundle_id}.json"
    if not path.is_file():
        extra = env_bundle_dir()
        if extra:
            path = extra / f"{bundle_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"semantic bundle not found: {bundle_id}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if int(raw.get("version", 0)) != version:
        raise ValueError(
            f"bundle version mismatch: {bundle_id} want {version} got {raw.get('version')}"
        )
    return SemanticBundleManifest.model_validate(raw)


def list_builtin_bundle_ids() -> list[str]:
    d = _bundles_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def env_bundle_dir() -> Path | None:
    v = os.environ.get("VERMYTH_ARCANE_BUNDLE_DIR")
    return Path(v) if v else None
