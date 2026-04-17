"""Derived bundle adoption report from local telemetry (decision support, not analytics)."""

from __future__ import annotations

from typing import Any

from vermyth.arcane.bundle_telemetry import get_bundle_adoption_summary
from vermyth.arcane.discovery import list_bundle_ids, load_primary_bundle_manifest

_ET = "bundle_recommended"
_IT = "bundle_inspected"
_VT = "bundle_invoked"
_MT = "bundle_recommendation_missed"


def _ratio(num: float, den: float) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 4)


def _canonical_bundle_ids() -> dict[str, str]:
    """bundle_id -> library tier (canonical | extended | unset)."""
    out: dict[str, str] = {}
    for bid in list_bundle_ids():
        try:
            m = load_primary_bundle_manifest(bid)
        except (FileNotFoundError, ValueError, OSError):
            continue
        tier = m.library or "unset"
        out[bid] = tier
    return out


def build_bundle_adoption_report(
    *,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a structured report from ``get_bundle_adoption_summary()`` for local review.

    Ratios are **approximate** session views: they relate event counts, not unique sessions.
    """
    summary = summary if summary is not None else get_bundle_adoption_summary()
    canonical_map = _canonical_bundle_ids()

    if not summary.get("enabled"):
        return {
            "schema_version": 1,
            "telemetry_enabled": False,
            "missed_detection_enabled": summary.get("missed_detection_enabled", False),
            "note": (
                "Set VERMYTH_BUNDLE_TELEMETRY=1 to record events, then refresh this report. "
                "Optional VERMYTH_BUNDLE_TELEMETRY_MISSED=1 records missed-upgrade signals on plain invocations."
            ),
            "raw_summary": summary,
        }

    per = summary.get("per_bundle_event_counts") or {}
    bytes_by = summary.get("bytes_saved_estimate_by_bundle") or {}

    rows: list[dict[str, Any]] = []
    for bid in sorted(set(per) | set(bytes_by)):
        ev = per.get(bid, {})
        r = int(ev.get(_ET, 0))
        i = int(ev.get(_IT, 0))
        v = int(ev.get(_VT, 0))
        m = int(ev.get(_MT, 0))
        bsum = int(bytes_by.get(bid, 0))
        avg_saved = _ratio(float(bsum), float(v)) if v else None

        rows.append(
            {
                "bundle_id": bid,
                "library": canonical_map.get(bid, "unset"),
                "counts": {
                    "bundle_recommended": r,
                    "bundle_inspected": i,
                    "bundle_invoked": v,
                    "bundle_recommendation_missed": m,
                },
                "ratios": {
                    "inspect_per_recommend": _ratio(float(i), float(r)),
                    "invoke_per_inspect": _ratio(float(v), float(i)),
                    "invoke_per_recommend": _ratio(float(v), float(r)),
                    "missed_per_recommend": _ratio(float(m), float(r)) if r else None,
                },
                "bytes_saved_estimate_total": bsum,
                "bytes_saved_estimate_per_invoke": avg_saved,
            }
        )

    by_rec = sorted(rows, key=lambda x: -x["counts"]["bundle_recommended"])
    by_inv = sorted(rows, key=lambda x: -x["counts"]["bundle_invoked"])
    by_miss = sorted(rows, key=lambda x: -x["counts"]["bundle_recommendation_missed"])

    findings: list[dict[str, Any]] = []
    for row in rows:
        bid = row["bundle_id"]
        c = row["counts"]
        r, i, v, m = (
            c["bundle_recommended"],
            c["bundle_inspected"],
            c["bundle_invoked"],
            c["bundle_recommendation_missed"],
        )
        if r >= 3 and i < max(1, int(r * 0.25)):
            findings.append(
                {
                    "kind": "recommended_low_inspect",
                    "severity": "info",
                    "bundle_id": bid,
                    "message": (
                        f"Bundle {bid!r} is often recommended ({r}) but rarely inspected ({i}); "
                        "consider improving discoverability or guided-upgrade visibility."
                    ),
                }
            )
        if m >= 3 and m > v + 1:
            findings.append(
                {
                    "kind": "high_missed_vs_invoke",
                    "severity": "warning",
                    "bundle_id": bid,
                    "message": (
                        f"Bundle {bid!r} has more missed-upgrade signals ({m}) than invocations ({v}); "
                        "callers may be ignoring suggestions or missing VERMYTH_BUNDLE_TELEMETRY_MISSED=1 elsewhere."
                    ),
                }
            )
        btot = int(row.get("bytes_saved_estimate_total", 0))
        if v >= 2 and btot > 0 and btot >= 50 * v:
            findings.append(
                {
                    "kind": "strong_bytes_signal",
                    "severity": "info",
                    "bundle_id": bid,
                    "message": (
                        f"Bundle {bid!r} is invoked ({v}) with notable aggregate bytes saved estimate "
                        f"({btot}); bundle-first may be paying off."
                    ),
                }
            )

    # Dedupe findings by (kind, bundle_id) keeping first
    seen: set[tuple[str, str]] = set()
    uniq: list[dict[str, Any]] = []
    for f in findings:
        k = (str(f["kind"]), str(f["bundle_id"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)

    return {
        "schema_version": 1,
        "telemetry_enabled": True,
        "missed_detection_enabled": summary.get("missed_detection_enabled", False),
        "approximations": {
            "ratios": (
                "Counts are event totals, not unique users or sessions; "
                "ratios are descriptive only."
            ),
            "bytes": summary.get("note", ""),
        },
        "totals_by_event_type": dict(summary.get("counts_by_event_type") or {}),
        "canonical_bundle_library": canonical_map,
        "per_bundle": rows,
        "top_by_recommended": [x["bundle_id"] for x in by_rec[:8]],
        "top_by_invoked": [x["bundle_id"] for x in by_inv[:8]],
        "top_by_missed": [x["bundle_id"] for x in by_miss[:8]],
        "findings": uniq,
        "raw_summary": summary,
    }


__all__ = ["build_bundle_adoption_report"]
