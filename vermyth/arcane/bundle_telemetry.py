"""Local, opt-in bundle adoption telemetry (no external services, no raw payload storage)."""

from __future__ import annotations

import json
import os
import threading
import time
from collections import Counter
from collections.abc import Mapping
from typing import Any

# Enable event recording (in-memory only).
ENV_ENABLE = "VERMYTH_BUNDLE_TELEMETRY"
# When enabled with main flag, run recommendation matching on plain invocations to detect missed upgrades.
ENV_MISSED = "VERMYTH_BUNDLE_TELEMETRY_MISSED"

_MAX_RECENT = 200

_lock = threading.Lock()
_counts_by_event: Counter[str] = Counter()
_counts_by_bundle: Counter[str] = Counter()
_bundle_event_matrix: Counter[tuple[str, str]] = Counter()
_bytes_saved_total = 0
_bytes_saved_by_bundle: Counter[str] = Counter()
_recent: list[dict[str, Any]] = []


def is_enabled() -> bool:
    return bool(int(os.environ.get(ENV_ENABLE, "0") or "0"))


def missed_detection_enabled() -> bool:
    if not is_enabled():
        return False
    return bool(int(os.environ.get(ENV_MISSED, "0") or "0"))


def reset_for_tests() -> None:
    """Clear all counters and recent events (tests only)."""
    global _bytes_saved_total
    with _lock:
        _counts_by_event.clear()
        _counts_by_bundle.clear()
        _bundle_event_matrix.clear()
        _bytes_saved_total = 0
        _bytes_saved_by_bundle.clear()
        _recent.clear()


def _append_recent(event: dict[str, Any]) -> None:
    with _lock:
        _recent.append(event)
        while len(_recent) > _MAX_RECENT:
            _recent.pop(0)


def _bump(event_type: str, bundle_id: str | None) -> None:
    with _lock:
        _counts_by_event[event_type] += 1
        if bundle_id:
            _counts_by_bundle[bundle_id] += 1
            _bundle_event_matrix[(bundle_id, event_type)] += 1


def record_bundle_recommended(
    *,
    surface: str,
    skill_id: str,
    bundle_id: str,
    version: int,
    strength: float,
    match_kind: str,
    target_skill: str,
) -> None:
    if not is_enabled():
        return
    ev = {
        "ts": time.time(),
        "event_type": "bundle_recommended",
        "surface": surface,
        "target_skill": target_skill,
        "skill_id": skill_id,
        "bundle_id": bundle_id,
        "version": version,
        "strength": strength,
        "match_kind": match_kind,
        "used_semantic_bundle": False,
    }
    _bump("bundle_recommended", bundle_id)
    _append_recent(ev)


def record_bundle_catalog_listed(*, surface: str, kind: str | None) -> None:
    if not is_enabled():
        return
    ev = {
        "ts": time.time(),
        "event_type": "bundle_catalog_listed",
        "surface": surface,
        "kind_filter": kind,
    }
    _bump("bundle_catalog_listed", None)
    _append_recent(ev)


def record_bundle_inspected(
    *,
    surface: str,
    bundle_id: str,
    version: int,
    guided_upgrade_shown: bool = True,
) -> None:
    if not is_enabled():
        return
    ev = {
        "ts": time.time(),
        "event_type": "bundle_inspected",
        "surface": surface,
        "bundle_id": bundle_id,
        "version": version,
        "guided_upgrade_shown": guided_upgrade_shown,
    }
    _bump("bundle_inspected", bundle_id)
    _append_recent(ev)


def record_bundle_invoked(
    *,
    surface: str,
    bundle_id: str,
    version: int,
    target_skill: str,
    ref_bytes: int | None,
    expanded_bytes: int | None,
) -> None:
    if not is_enabled():
        return
    global _bytes_saved_total
    saved = 0
    if ref_bytes is not None and expanded_bytes is not None and expanded_bytes >= ref_bytes:
        saved = expanded_bytes - ref_bytes
    ev = {
        "ts": time.time(),
        "event_type": "bundle_invoked",
        "surface": surface,
        "bundle_id": bundle_id,
        "version": version,
        "target_skill": target_skill,
        "ref_bytes": ref_bytes,
        "expanded_bytes": expanded_bytes,
        "bytes_saved_estimate": saved,
        "used_semantic_bundle": True,
    }
    with _lock:
        _counts_by_event["bundle_invoked"] += 1
        _counts_by_bundle[bundle_id] += 1
        _bundle_event_matrix[(bundle_id, "bundle_invoked")] += 1
        _bytes_saved_total += saved
        _bytes_saved_by_bundle[bundle_id] += saved
    _append_recent(ev)


def record_bundle_recommendation_missed(
    *,
    surface: str,
    skill_id: str,
    bundle_id: str,
    version: int,
    strength: float,
    match_kind: str,
    target_skill: str,
) -> None:
    if not is_enabled():
        return
    ev = {
        "ts": time.time(),
        "event_type": "bundle_recommendation_missed",
        "surface": surface,
        "skill_id": skill_id,
        "bundle_id": bundle_id,
        "version": version,
        "strength": strength,
        "match_kind": match_kind,
        "target_skill": target_skill,
        "used_semantic_bundle": False,
    }
    _bump("bundle_recommendation_missed", bundle_id)
    _append_recent(ev)


def _json_len(obj: Any) -> int:
    try:
        return len(json.dumps(obj, sort_keys=True, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return 0


def estimate_invocation_payload_metrics(
    ref: Mapping[str, Any], merged_input: Mapping[str, Any]
) -> tuple[int, int]:
    """Return (semantic_bundle ref byte length, merged expanded input byte length)."""
    compact = {"semantic_bundle": dict(ref)}
    return _json_len(compact), _json_len(dict(merged_input))


def get_bundle_adoption_summary() -> dict[str, Any]:
    """Read-only aggregate for local review (no external I/O)."""
    with _lock:
        by_event = dict(_counts_by_event)
        by_bundle = dict(_counts_by_bundle)
        recent = list(_recent[-50:])
        btot = _bytes_saved_total
        mat_items = list(_bundle_event_matrix.items())
        bsb = dict(_bytes_saved_by_bundle)
    per_bundle: dict[str, dict[str, int]] = {}
    for (bid, et), c in mat_items:
        per_bundle.setdefault(bid, {})[et] = c
    funnel = {
        "bundle_recommended": by_event.get("bundle_recommended", 0),
        "bundle_catalog_listed": by_event.get("bundle_catalog_listed", 0),
        "bundle_inspected": by_event.get("bundle_inspected", 0),
        "bundle_invoked": by_event.get("bundle_invoked", 0),
        "bundle_recommendation_missed": by_event.get("bundle_recommendation_missed", 0),
    }
    return {
        "enabled": is_enabled(),
        "missed_detection_enabled": missed_detection_enabled(),
        "counts_by_event_type": by_event,
        "counts_by_bundle_id": by_bundle,
        "per_bundle_event_counts": per_bundle,
        "bytes_saved_estimate_by_bundle": bsb,
        "funnel": funnel,
        "bytes_saved_estimate_total": btot,
        "note": (
            "Local in-memory counters only; no network export. "
            "bytes_saved_estimate is len(expanded_json)-len(ref_json) when both are known; approximate."
        ),
        "recent_events_sample": recent,
    }


__all__ = [
    "ENV_ENABLE",
    "ENV_MISSED",
    "estimate_invocation_payload_metrics",
    "get_bundle_adoption_summary",
    "is_enabled",
    "missed_detection_enabled",
    "record_bundle_catalog_listed",
    "record_bundle_inspected",
    "record_bundle_invoked",
    "record_bundle_recommended",
    "record_bundle_recommendation_missed",
    "reset_for_tests",
]
