"""Bundle adoption report derived from telemetry."""

from __future__ import annotations

import os

import pytest

from vermyth.arcane.bundle_adoption_report import build_bundle_adoption_report
from vermyth.arcane.bundle_telemetry import ENV_ENABLE, ENV_MISSED, reset_for_tests


@pytest.fixture(autouse=True)
def _reset():
    reset_for_tests()
    yield
    reset_for_tests()


def test_report_when_telemetry_disabled():
    os.environ[ENV_ENABLE] = "0"
    os.environ.pop(ENV_MISSED, None)
    r = build_bundle_adoption_report()
    assert r["telemetry_enabled"] is False
    assert "note" in r


def test_report_from_synthetic_summary():
    """Report logic without requiring live telemetry recording."""
    summary = {
        "enabled": True,
        "missed_detection_enabled": True,
        "counts_by_event_type": {
            "bundle_recommended": 10,
            "bundle_inspected": 2,
            "bundle_invoked": 3,
            "bundle_recommendation_missed": 8,
        },
        "counts_by_bundle_id": {},
        "per_bundle_event_counts": {
            "alpha": {
                "bundle_recommended": 5,
                "bundle_inspected": 1,
                "bundle_invoked": 2,
                "bundle_recommendation_missed": 4,
            },
            "beta": {
                "bundle_recommended": 1,
                "bundle_inspected": 1,
                "bundle_invoked": 1,
                "bundle_recommendation_missed": 0,
            },
        },
        "bytes_saved_estimate_by_bundle": {"alpha": 400, "beta": 10},
        "funnel": {},
        "bytes_saved_estimate_total": 410,
        "note": "test",
        "recent_events_sample": [],
    }
    r = build_bundle_adoption_report(summary=summary)
    assert r["telemetry_enabled"] is True
    assert r["totals_by_event_type"]["bundle_recommended"] == 10
    assert "alpha" in r["top_by_recommended"]
    per = {x["bundle_id"]: x for x in r["per_bundle"]}
    assert per["alpha"]["counts"]["bundle_recommended"] == 5
    assert per["alpha"]["ratios"]["invoke_per_recommend"] is not None
    assert per["alpha"]["bytes_saved_estimate_total"] == 400
    assert any(f["kind"] == "high_missed_vs_invoke" for f in r["findings"] if f["bundle_id"] == "alpha")


def test_funnel_ratios_zero_division():
    summary = {
        "enabled": True,
        "missed_detection_enabled": False,
        "counts_by_event_type": {},
        "per_bundle_event_counts": {
            "gamma": {"bundle_invoked": 2},
        },
        "bytes_saved_estimate_by_bundle": {},
        "recent_events_sample": [],
    }
    r = build_bundle_adoption_report(summary=summary)
    per = next(x for x in r["per_bundle"] if x["bundle_id"] == "gamma")
    assert per["ratios"]["inspect_per_recommend"] is None


def test_mcp_tool_returns_report(tmp_path):
    from vermyth.engine.composition import CompositionEngine
    from vermyth.engine.resonance import ResonanceEngine
    from vermyth.grimoire.store import Grimoire
    from vermyth.mcp.server import VermythMCPServer
    import io
    import json

    os.environ[ENV_ENABLE] = "1"
    db = tmp_path / "r.db"
    eng = ResonanceEngine(CompositionEngine(), None)
    g = Grimoire(db_path=db)
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=out,
        stderr=io.StringIO(),
        engine=eng,
        grimoire=g,
    )
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "get_bundle_adoption_report", "arguments": {}},
        }
    )
    out.seek(0)
    resp = json.loads(out.read())
    assert "result" in resp
    assert "schema_version" in resp["result"]
